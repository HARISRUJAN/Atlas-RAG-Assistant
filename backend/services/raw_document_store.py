"""Service for managing raw documents in MongoDB Atlas."""

from typing import List, Optional, Dict, Any
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from datetime import datetime

from backend.config import Config
from backend.models.raw_document import RawDocument


class RawDocumentStore:
    """Service for raw_documents collection operations."""
    
    def __init__(self, database_name: Optional[str] = None, collection_name: Optional[str] = None, mongodb_uri: Optional[str] = None):
        """
        Initialize raw document store.
        
        Args:
            database_name: Optional database name. Defaults to Config.RAW_DOCUMENTS_DATABASE_NAME
            collection_name: Optional collection name. Defaults to Config.RAW_DOCUMENTS_COLLECTION_NAME
            mongodb_uri: Optional MongoDB URI. Defaults to Config.MONGODB_URI
        """
        self.database_name = database_name or Config.RAW_DOCUMENTS_DATABASE_NAME
        self.collection_name = collection_name or Config.RAW_DOCUMENTS_COLLECTION_NAME
        self.mongodb_uri = mongodb_uri or Config.MONGODB_URI
        
        if not self.mongodb_uri:
            raise ValueError("MongoDB URI is required for RawDocumentStore")
        
        # Configure MongoDB client
        connection_params = {
            'serverSelectionTimeoutMS': 30000,
            'connectTimeoutMS': 30000,
            'socketTimeoutMS': 30000,
        }
        
        if self.mongodb_uri.startswith('mongodb+srv://'):
            if 'retryWrites' not in self.mongodb_uri:
                separator = '&' if '?' in self.mongodb_uri else '?'
                uri_with_params = f"{self.mongodb_uri}{separator}retryWrites=true&w=majority"
            else:
                uri_with_params = self.mongodb_uri
        else:
            connection_params['tls'] = True
            connection_params['tlsAllowInvalidCertificates'] = False
            uri_with_params = self.mongodb_uri
        
        try:
            self.client = MongoClient(uri_with_params, **connection_params)
            self.client.admin.command('ping')
        except Exception as e:
            error_msg = str(e)
            if 'SSL' in error_msg or 'TLS' in error_msg:
                print("\n" + "="*70)
                print("SSL/TLS CONNECTION ERROR DETECTED")
                print("="*70)
                print("\nYour connection string should be in this format:")
                print("mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority")
                print("="*70 + "\n")
            raise
        
        self.db = self.client[self.database_name]
        self.collection = self.db[self.collection_name]
        
        # Create indexes
        self._ensure_indexes()
        
        # Cache for semantic collection indexes (to avoid repeated index creation)
        self._semantic_indexes_ensured = set()
        
        # Cache for semantic collection indexes (to avoid repeated index creation)
        self._semantic_indexes_ensured = set()
    
    def _ensure_indexes(self):
        """Ensure required indexes exist."""
        try:
            # Unique index on origin_id to prevent duplicates
            # Note: This will fail if duplicates already exist, so we handle that gracefully
            try:
                self.collection.create_index('origin_id', unique=True)
                print("[RawDocumentStore] Created unique index on origin_id")
            except OperationFailure as e:
                # Index might already exist or there might be duplicates
                if 'duplicate key' not in str(e).lower() and 'already exists' not in str(e).lower():
                    print(f"[RawDocumentStore] Warning: Could not create unique index on origin_id: {e}")
            
            # Index on status for filtering
            self.collection.create_index('status')
            # Index on origin_source_type and origin_source_id
            self.collection.create_index([('origin_source_type', 1), ('origin_source_id', 1)])
            # Index on created_at for sorting
            self.collection.create_index('created_at')
        except Exception as e:
            print(f"[RawDocumentStore] Warning: Could not create indexes: {e}")
    
    def is_origin_ingested(self, origin_id: str, origin_source_type: Optional[str] = None) -> bool:
        """
        Check if an origin document has already been ingested.
        
        Args:
            origin_id: Origin document ID
            origin_source_type: Optional origin source type for additional filtering
            
        Returns:
            True if document with this origin_id already exists
        """
        try:
            query = {'origin_id': origin_id}
            if origin_source_type:
                query['origin_source_type'] = origin_source_type
            
            existing = self.collection.find_one(query)
            return existing is not None
        except Exception as e:
            print(f"[RawDocumentStore] Error checking if origin is ingested: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test MongoDB connection."""
        try:
            self.client.admin.command('ping')
            return True
        except ConnectionFailure:
            return False
    
    def store_raw_document(self, raw_doc: RawDocument) -> str:
        """
        Store a raw document.
        
        Args:
            raw_doc: RawDocument instance
            
        Returns:
            The raw_document_id
            
        Raises:
            Exception: If storage fails (including duplicate key errors)
        """
        try:
            doc_dict = raw_doc.to_dict()
            result = self.collection.insert_one(doc_dict)
            return raw_doc.raw_document_id
        except OperationFailure as e:
            error_str = str(e)
            # Check for duplicate key error (E11000)
            if 'E11000' in error_str or 'duplicate key' in error_str.lower():
                print(f"[RawDocumentStore] Duplicate key error for origin_id: {raw_doc.origin_id}")
                # Try to get existing document
                existing = self.get_raw_document_by_origin_id(raw_doc.origin_id, raw_doc.origin_source_type)
                if existing:
                    print(f"[RawDocumentStore] Document with origin_id '{raw_doc.origin_id}' already exists: {existing.raw_document_id}")
                    return existing.raw_document_id
                # If we can't find it, raise a user-friendly error
                raise ValueError(f"Document with origin_id '{raw_doc.origin_id}' already exists in the system")
            # Transform other MongoDB errors to user-friendly messages
            if 'timeout' in error_str.lower():
                raise ConnectionError("Database operation timed out. Please try again.")
            print(f"[RawDocumentStore] Error storing raw document: {e}")
            raise ValueError(f"Failed to store document: {error_str}")
        except Exception as e:
            error_str = str(e)
            # Don't double-wrap ValueError
            if isinstance(e, ValueError):
                raise
            print(f"[RawDocumentStore] Error storing raw document: {error_str}")
            raise ValueError(f"Failed to store document: {error_str}")
    
    def store_raw_document_upsert(self, raw_doc: RawDocument) -> Dict[str, Any]:
        """
        Store a raw document using upsert pattern (atomic duplicate handling).
        This method is idempotent - safe to retry.
        
        Args:
            raw_doc: RawDocument instance
            
        Returns:
            Dictionary with:
                - raw_document_id: The raw document ID
                - was_inserted: True if document was inserted, False if updated
                - was_duplicate: True if document already existed
        """
        try:
            doc_dict = raw_doc.to_dict()
            
            # Use replace_one with upsert=True, filtering by origin_id
            # This makes the operation atomic and idempotent
            filter_query = {'origin_id': raw_doc.origin_id}
            if raw_doc.origin_source_type:
                filter_query['origin_source_type'] = raw_doc.origin_source_type
            
            result = self.collection.replace_one(
                filter_query,
                doc_dict,
                upsert=True
            )
            
            was_inserted = result.upserted_id is not None
            was_duplicate = not was_inserted
            
            if was_inserted:
                print(f"[RawDocumentStore] Inserted new raw document: {raw_doc.raw_document_id} (origin_id: {raw_doc.origin_id})")
            else:
                # Document was updated/replaced, get the existing raw_document_id
                existing = self.get_raw_document_by_origin_id(raw_doc.origin_id, raw_doc.origin_source_type)
                if existing:
                    # Use existing raw_document_id instead of the new one
                    raw_doc.raw_document_id = existing.raw_document_id
                    print(f"[RawDocumentStore] Updated existing raw document: {existing.raw_document_id} (origin_id: {raw_doc.origin_id})")
                else:
                    print(f"[RawDocumentStore] Upserted document but couldn't retrieve it (origin_id: {raw_doc.origin_id})")
            
            return {
                'raw_document_id': raw_doc.raw_document_id,
                'was_inserted': was_inserted,
                'was_duplicate': was_duplicate
            }
        except Exception as e:
            print(f"[RawDocumentStore] Error in store_raw_document_upsert: {e}")
            raise
    
    def get_raw_document_by_origin_id(self, origin_id: str, origin_source_type: Optional[str] = None) -> Optional[RawDocument]:
        """
        Get a raw document by origin_id.
        
        Args:
            origin_id: Origin document ID
            origin_source_type: Optional origin source type for additional filtering
            
        Returns:
            RawDocument instance or None
        """
        try:
            query = {'origin_id': origin_id}
            if origin_source_type:
                query['origin_source_type'] = origin_source_type
            
            doc = self.collection.find_one(query)
            if not doc:
                return None
            
            return RawDocument.from_dict(doc)
        except Exception as e:
            print(f"[RawDocumentStore] Error getting raw document by origin_id: {e}")
            return None
    
    def get_raw_document(self, raw_document_id: str) -> Optional[RawDocument]:
        """
        Get a raw document by ID.
        
        Args:
            raw_document_id: Raw document ID
            
        Returns:
            RawDocument instance or None
        """
        try:
            doc = self.collection.find_one({'raw_document_id': raw_document_id})
            if doc:
                return RawDocument.from_dict(doc)
            return None
        except Exception as e:
            print(f"[RawDocumentStore] Error getting raw document: {e}")
            return None
    
    def list_raw_documents(
        self,
        status: Optional[str] = None,
        origin_source_type: Optional[str] = None,
        origin_source_id: Optional[str] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[RawDocument]:
        """
        List raw documents with optional filters.
        
        Args:
            status: Filter by status ('pending', 'processing', 'processed', 'failed')
            origin_source_type: Filter by origin source type
            origin_source_id: Filter by origin source ID
            limit: Maximum number of documents to return
            skip: Number of documents to skip
            
        Returns:
            List of RawDocument instances
        """
        try:
            # Check if collection exists and has any documents
            # Use try-except in case collection doesn't exist yet
            try:
                collection_count = self.collection.count_documents({})
                if collection_count == 0:
                    print(f"[RawDocumentStore] Collection {self.database_name}.{self.collection_name} is empty")
                    return []
            except Exception as count_error:
                # Collection might not exist yet, which is fine - return empty list
                print(f"[RawDocumentStore] Collection {self.database_name}.{self.collection_name} doesn't exist yet or error counting: {count_error}")
                return []
            
            query = {}
            if status:
                query['status'] = status
            if origin_source_type:
                query['origin_source_type'] = origin_source_type
            if origin_source_id:
                query['origin_source_id'] = origin_source_id
            
            cursor = self.collection.find(query).sort('created_at', -1).skip(skip).limit(limit)
            documents = []
            for doc in cursor:
                try:
                    documents.append(RawDocument.from_dict(doc))
                except Exception as doc_error:
                    print(f"[RawDocumentStore] Error parsing document {doc.get('_id', 'unknown')}: {doc_error}")
                    import traceback
                    traceback.print_exc()
                    # Skip this document but continue with others
                    continue
            return documents
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"[RawDocumentStore] Error listing raw documents: {error_trace}")
            raise  # Re-raise to be caught by route handler
    
    def update_status(self, raw_document_id: str, status: str, error_message: Optional[str] = None):
        """
        Update raw document status.
        
        Args:
            raw_document_id: Raw document ID
            status: New status
            error_message: Optional error message
        """
        try:
            update_data = {'status': status}
            if status == 'processed':
                update_data['processed_at'] = datetime.utcnow()
            if error_message:
                update_data['error_message'] = error_message
            
            self.collection.update_one(
                {'raw_document_id': raw_document_id},
                {'$set': update_data}
            )
        except Exception as e:
            print(f"[RawDocumentStore] Error updating status: {e}")
            raise
    
    def delete_raw_document(self, raw_document_id: str) -> bool:
        """
        Delete a raw document.
        
        Args:
            raw_document_id: Raw document ID
            
        Returns:
            True if deleted
        """
        try:
            result = self.collection.delete_one({'raw_document_id': raw_document_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"[RawDocumentStore] Error deleting raw document: {e}")
            return False
    
    def count_by_status(self) -> Dict[str, int]:
        """
        Count raw documents by status.
        
        Returns:
            Dictionary mapping status to count
        """
        try:
            pipeline = [
                {'$group': {'_id': '$status', 'count': {'$sum': 1}}}
            ]
            results = list(self.collection.aggregate(pipeline))
            return {result['_id']: result['count'] for result in results}
        except Exception as e:
            print(f"[RawDocumentStore] Error counting by status: {e}")
            return {}
    
    def get_semantic_collection(self, origin_collection_name: Optional[str] = None, origin_db_name: Optional[str] = None):
        """
        Get or create semantic collection reference.
        
        Args:
            origin_collection_name: Origin collection name. Defaults to Config.ORIGIN_COLLECTION_NAME
            origin_db_name: Origin database name. Defaults to Config.ORIGIN_DB_NAME or self.database_name
            
        Returns:
            MongoDB collection object for semantic collection
        """
        origin_collection = origin_collection_name or Config.ORIGIN_COLLECTION_NAME
        origin_db = origin_db_name or Config.ORIGIN_DB_NAME or self.database_name
        
        semantic_collection_name = Config.get_semantic_collection_name(origin_collection)
        semantic_db = self.client[origin_db]
        semantic_collection = semantic_db[semantic_collection_name]
        
        # Ensure indexes exist on semantic collection
        self._ensure_semantic_indexes(semantic_collection)
        
        return semantic_collection
    
    def _ensure_semantic_indexes(self, semantic_collection):
        """
        Ensure required indexes exist on semantic collection.
        This method is idempotent and uses caching to avoid repeated calls.
        
        Args:
            semantic_collection: MongoDB collection object for semantic collection
        """
        # Create cache key from collection full name
        collection_key = f"{semantic_collection.database.name}.{semantic_collection.name}"
        
        # Check cache to avoid repeated index creation
        if collection_key in self._semantic_indexes_ensured:
            return  # Indexes already ensured for this collection
        
        try:
            # Regular indexes for querying
            try:
                semantic_collection.create_index('origin_id')
                print(f"[RawDocumentStore] Created index on origin_id in semantic collection {collection_key}")
            except OperationFailure as e:
                if 'already exists' not in str(e).lower():
                    print(f"[RawDocumentStore] Warning: Could not create index on origin_id: {e}")
            
            try:
                semantic_collection.create_index('chunk_id')
                print(f"[RawDocumentStore] Created index on chunk_id in semantic collection {collection_key}")
            except OperationFailure as e:
                if 'already exists' not in str(e).lower():
                    print(f"[RawDocumentStore] Warning: Could not create index on chunk_id: {e}")
            
            # Compound index for (origin_id, chunk_id) uniqueness
            try:
                semantic_collection.create_index([('origin_id', 1), ('chunk_id', 1)], unique=True)
                print(f"[RawDocumentStore] Created unique compound index on (origin_id, chunk_id) in semantic collection {collection_key}")
            except OperationFailure as e:
                if 'already exists' not in str(e).lower() and 'duplicate key' not in str(e).lower():
                    print(f"[RawDocumentStore] Warning: Could not create unique index on (origin_id, chunk_id): {e}")
            
            # Mark as ensured in cache
            self._semantic_indexes_ensured.add(collection_key)
            
            # Note: Vector index on 'embedding' field must be created via MongoDB Atlas UI or admin script
            # This is not done here as it requires specific Atlas Vector Search configuration
            print(f"[RawDocumentStore] Note: Vector index on 'embedding' field must be created via MongoDB Atlas UI or migration script")
            
        except Exception as e:
            print(f"[RawDocumentStore] Warning: Could not create semantic indexes: {e}")
            # Don't add to cache if there was an error, so we can retry
    
    def store_semantic_chunk_upsert(
        self,
        origin_id: str,
        chunk_id: str,
        chunk_text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        origin_collection_name: Optional[str] = None,
        origin_db_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Store a semantic chunk using upsert pattern (atomic duplicate handling).
        This method is idempotent - safe to retry.
        
        Args:
            origin_id: Origin document ID
            chunk_id: Chunk identifier (deterministic per document)
            chunk_text: Text content of the chunk
            embedding: Vector embedding for the chunk
            metadata: Optional metadata dictionary
            origin_collection_name: Origin collection name. Defaults to Config.ORIGIN_COLLECTION_NAME
            origin_db_name: Origin database name. Defaults to Config.ORIGIN_DB_NAME or self.database_name
            
        Returns:
            Dictionary with:
                - doc_id: The document ID used
                - was_inserted: True if document was inserted, False if updated
                - was_duplicate: True if document already existed
        """
        try:
            semantic_collection = self.get_semantic_collection(origin_collection_name, origin_db_name)
            
            # Create unique document ID
            doc_id = f"{origin_id}:{chunk_id}"
            
            # Prepare document
            doc = {
                '_id': doc_id,
                'origin_id': origin_id,
                'chunk_id': chunk_id,
                'chunk_text': chunk_text,
                'embedding': embedding,
                'metadata': metadata or {},
            }
            
            # Use replace_one with upsert=True for idempotency
            result = semantic_collection.replace_one(
                {'_id': doc_id},
                doc,
                upsert=True
            )
            
            was_inserted = result.upserted_id is not None
            was_duplicate = not was_inserted
            
            if was_inserted:
                print(f"[RawDocumentStore] Inserted new semantic chunk: {doc_id}")
            else:
                print(f"[RawDocumentStore] Updated existing semantic chunk: {doc_id}")
            
            return {
                'doc_id': doc_id,
                'was_inserted': was_inserted,
                'was_duplicate': was_duplicate
            }
        except Exception as e:
            print(f"[RawDocumentStore] Error in store_semantic_chunk_upsert: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def has_semantic_chunks(self, origin_id: str, origin_collection_name: Optional[str] = None, origin_db_name: Optional[str] = None) -> bool:
        """
        Check if an origin document already has semantic chunks.
        
        Uses the same key strategy as store_semantic_chunk_upsert():
        - Queries by origin_id (chunks are stored with _id = "{origin_id}:{chunk_id}")
        - This matches the storage pattern exactly
        
        Args:
            origin_id: Origin document ID
            origin_collection_name: Origin collection name. Defaults to Config.ORIGIN_COLLECTION_NAME
            origin_db_name: Origin database name. Defaults to Config.ORIGIN_DB_NAME or self.database_name
            
        Returns:
            True if semantic chunks exist for this origin_id
        """
        try:
            semantic_collection = self.get_semantic_collection(origin_collection_name, origin_db_name)
            # Query by origin_id - this matches how chunks are stored
            # Chunks have _id = "{origin_id}:{chunk_id}" and also have origin_id field
            # Using origin_id field query is efficient with the index we create
            count = semantic_collection.count_documents({'origin_id': origin_id})
            return count > 0
        except Exception as e:
            print(f"[RawDocumentStore] Error checking for semantic chunks: {e}")
            return False
    
    def close(self):
        """Close MongoDB connection."""
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                print(f"[RawDocumentStore] Error closing client: {e}")

