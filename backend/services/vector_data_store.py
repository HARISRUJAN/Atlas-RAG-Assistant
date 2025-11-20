"""Service for managing vector data in MongoDB Atlas."""

from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

from backend.config import Config
from backend.models.document import DocumentChunk


class VectorDataStore:
    """Service for vector_data collection operations with vector search."""
    
    def __init__(self, database_name: Optional[str] = None, collection_name: Optional[str] = None, index_name: Optional[str] = None, mongodb_uri: Optional[str] = None):
        """
        Initialize vector data store.
        
        Args:
            database_name: Optional database name. Defaults to Config.VECTOR_DATA_DATABASE_NAME
            collection_name: Optional collection name. Can be "collection" or "database.collection" format.
                           Defaults to Config.VECTOR_DATA_COLLECTION_NAME
            index_name: Optional index name. Defaults to Config.VECTOR_DATA_INDEX_NAME
            mongodb_uri: Optional MongoDB URI. Defaults to Config.MONGODB_URI
        """
        # Parse collection_name if it's in database.collection format
        if collection_name and '.' in collection_name:
            parts = collection_name.split('.', 1)
            if len(parts) == 2:
                self.database_name = parts[0]
                self.collection_name = parts[1]
            else:
                self.database_name = database_name or Config.VECTOR_DATA_DATABASE_NAME
                self.collection_name = collection_name
        else:
            self.database_name = database_name or Config.VECTOR_DATA_DATABASE_NAME
            self.collection_name = collection_name or Config.VECTOR_DATA_COLLECTION_NAME
        
        self.index_name = index_name or Config.VECTOR_DATA_INDEX_NAME
        self.mongodb_uri = mongodb_uri or Config.MONGODB_URI
        
        if not self.mongodb_uri:
            raise ValueError("MongoDB URI is required for VectorDataStore")
        
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
    
    def test_connection(self) -> bool:
        """Test MongoDB connection."""
        try:
            self.client.admin.command('ping')
            return True
        except ConnectionFailure:
            return False
    
    def store_chunks(self, chunks: List[DocumentChunk]) -> int:
        """
        Store document chunks with embeddings in vector_data collection.
        
        Args:
            chunks: List of DocumentChunk instances with embeddings
            
        Returns:
            Number of chunks stored
        """
        if not chunks:
            return 0
        
        try:
            documents = [chunk.to_dict() for chunk in chunks]
            result = self.collection.insert_many(documents)
            print(f"[VectorDataStore] Stored {len(result.inserted_ids)} chunks in vector_data collection")
            return len(result.inserted_ids)
        except Exception as e:
            print(f"[VectorDataStore] Error storing chunks: {e}")
            raise
    
    def vector_search(self, query_embedding: List[float], top_k: int = 5, filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search on vector_data collection.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filter_dict: Optional MongoDB filter to apply before vector search
            
        Returns:
            List of matching documents with scores
        """
        # Try multiple common index names
        # Order matters: try most common names first
        index_names_to_try = [
            self.index_name,  # Try configured name first
            'vector_index',  # Most common working name
            'default',  # Common default name
            'vector_data_index',  # Pipeline default
        ]
        # Remove duplicates while preserving order
        seen = set()
        index_names_to_try = [x for x in index_names_to_try if not (x in seen or seen.add(x))]
        
        print(f"[VectorDataStore] Attempting vector search with index names: {index_names_to_try}")
        print(f"[VectorDataStore] Query embedding dimensions: {len(query_embedding)}")
        print(f"[VectorDataStore] Collection: {self.database_name}.{self.collection_name}")
        
        last_error = None
        
        for index_name in index_names_to_try:
            try:
                # Build aggregation pipeline
                pipeline = [
                    {
                        "$vectorSearch": {
                            "index": index_name,
                            "path": "embedding",
                            "queryVector": query_embedding,
                            "numCandidates": max(top_k * 10, 100),  # Ensure at least 100 candidates
                            "limit": top_k
                        }
                    }
                ]
                
                # Add filter stage if provided
                if filter_dict:
                    pipeline.insert(0, {"$match": filter_dict})
                
                # Project fields
                pipeline.append({
                    "$project": {
                        "_id": 0,
                        "chunk_id": 1,
                        "document_id": 1,
                        "file_name": 1,
                        "chunk_index": 1,
                        "content": 1,
                        "line_start": 1,
                        "line_end": 1,
                        "metadata": 1,
                        "origin_id": 1,
                        "raw_document_id": 1,
                        "score": {"$meta": "vectorSearchScore"}
                    }
                })
                
                print(f"[VectorDataStore] Trying index name: '{index_name}'")
                results = list(self.collection.aggregate(pipeline))
                
                if results:
                    print(f"[VectorDataStore] ✓ SUCCESS with index '{index_name}': {len(results)} results")
                    # Log sample result for debugging
                    if results[0].get('content'):
                        sample_content = results[0]['content'][:100] + "..." if len(results[0]['content']) > 100 else results[0]['content']
                        print(f"[VectorDataStore] Sample result content: {sample_content}")
                    return results
                else:
                    print(f"[VectorDataStore] Index '{index_name}' exists but returned 0 results")
                    # Continue to next index name
                    continue
                    
            except OperationFailure as e:
                error_msg = str(e)
                last_error = error_msg
                print(f"[VectorDataStore] Index '{index_name}' failed: {error_msg}")
                
                # If error mentions index not found, try next index name
                if 'index' in error_msg.lower() or 'not found' in error_msg.lower():
                    print(f"[VectorDataStore] Index '{index_name}' not found, trying next...")
                    continue
                else:
                    # Other operation failure - might be a real error
                    print(f"[VectorDataStore] Operation failure with index '{index_name}': {error_msg}")
                    # Still try next index in case it's just the wrong name
                    continue
                    
            except Exception as e:
                error_msg = str(e)
                last_error = error_msg
                print(f"[VectorDataStore] Unexpected error with index '{index_name}': {error_msg}")
                import traceback
                traceback.print_exc()
                # Try next index
                continue
        
        # All index names failed
        print(f"[VectorDataStore] ✗ All index names failed. Last error: {last_error}")
        
        # Check if collection has documents
        try:
            doc_count = self.collection.count_documents({})
            print(f"[VectorDataStore] Collection has {doc_count} documents")
            
            # Check if documents have embeddings
            doc_with_embedding = self.collection.count_documents({"embedding": {"$exists": True}})
            print(f"[VectorDataStore] Documents with embeddings: {doc_with_embedding}")
            
            if doc_count == 0:
                print("[VectorDataStore] Collection is empty - no documents to search")
                return []
            
            if doc_with_embedding == 0:
                print("[VectorDataStore] WARNING: No documents have embeddings!")
                return []
            
            # Check embedding dimensions
            sample_doc = self.collection.find_one({"embedding": {"$exists": True}})
            if sample_doc and 'embedding' in sample_doc:
                emb = sample_doc['embedding']
                if isinstance(emb, list):
                    print(f"[VectorDataStore] Sample embedding dimensions: {len(emb)}")
                    print(f"[VectorDataStore] Query embedding dimensions: {len(query_embedding)}")
                    if len(emb) != len(query_embedding):
                        print(f"[VectorDataStore] ERROR: Embedding dimension mismatch! Documents: {len(emb)}, Query: {len(query_embedding)}")
                else:
                    print(f"[VectorDataStore] WARNING: Embedding is not a list: {type(emb)}")
        except Exception as check_error:
            print(f"[VectorDataStore] Error checking collection: {check_error}")
        
        return []
    
    def delete_by_raw_document_id(self, raw_document_id: str) -> int:
        """
        Delete all chunks associated with a raw document.
        
        Args:
            raw_document_id: Raw document ID
            
        Returns:
            Number of chunks deleted
        """
        try:
            result = self.collection.delete_many({'raw_document_id': raw_document_id})
            print(f"[VectorDataStore] Deleted {result.deleted_count} chunks for raw_document_id: {raw_document_id}")
            return result.deleted_count
        except Exception as e:
            print(f"[VectorDataStore] Error deleting chunks: {e}")
            return 0
    
    def delete_by_origin_id(self, origin_id: str) -> int:
        """
        Delete all chunks associated with an origin document.
        
        Args:
            origin_id: Origin document ID
            
        Returns:
            Number of chunks deleted
        """
        try:
            result = self.collection.delete_many({'origin_id': origin_id})
            print(f"[VectorDataStore] Deleted {result.deleted_count} chunks for origin_id: {origin_id}")
            return result.deleted_count
        except Exception as e:
            print(f"[VectorDataStore] Error deleting chunks: {e}")
            return 0
    
    def count_chunks(self, filter_dict: Optional[Dict[str, Any]] = None) -> int:
        """
        Count chunks in vector_data collection.
        
        Args:
            filter_dict: Optional MongoDB filter
            
        Returns:
            Number of chunks
        """
        try:
            if filter_dict:
                return self.collection.count_documents(filter_dict)
            return self.collection.count_documents({})
        except Exception as e:
            print(f"[VectorDataStore] Error counting chunks: {e}")
            return 0
    
    def close(self):
        """Close MongoDB connection."""
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                print(f"[VectorDataStore] Error closing client: {e}")

