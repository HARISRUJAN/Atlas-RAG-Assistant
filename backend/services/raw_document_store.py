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
        """
        try:
            doc_dict = raw_doc.to_dict()
            result = self.collection.insert_one(doc_dict)
            return raw_doc.raw_document_id
        except Exception as e:
            print(f"[RawDocumentStore] Error storing raw document: {e}")
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
    
    def close(self):
        """Close MongoDB connection."""
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                print(f"[RawDocumentStore] Error closing client: {e}")

