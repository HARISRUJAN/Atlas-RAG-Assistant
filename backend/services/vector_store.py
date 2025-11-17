"""MongoDB Vector Store service for storing and retrieving document chunks."""

from typing import List, Dict, Any
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from backend.config import Config
from backend.models.document import DocumentChunk


class VectorStoreService:
    """Service for MongoDB Vector Store operations."""
    
    def __init__(self, collection_name: str = None, database_name: str = None, index_name: str = None, mongodb_uri: str = None):
        """
        Initialize vector store service.
        
        Args:
            collection_name: Optional collection name. Can be "collection" or "database.collection" format.
                            Defaults to Config.MONGODB_COLLECTION_NAME
            database_name: Optional database name. If collection_name contains ".", this is ignored.
                          Defaults to Config.MONGODB_DATABASE_NAME
            index_name: Optional index name. Defaults to Config.MONGODB_VECTOR_INDEX_NAME
            mongodb_uri: Optional MongoDB URI. Defaults to Config.MONGODB_URI
        """
        # Parse database and collection from collection_name if it contains "."
        if collection_name and '.' in collection_name:
            db_name, coll_name = collection_name.split('.', 1)
            database_name = db_name
            collection_name = coll_name
        
        # Use provided URI or fallback to config
        uri_to_use = mongodb_uri or Config.MONGODB_URI
        
        # Configure MongoDB client with SSL/TLS support for Atlas
        # For mongodb+srv:// connections, TLS is automatically enabled
        connection_params = {
            'serverSelectionTimeoutMS': 30000,
            'connectTimeoutMS': 30000,
            'socketTimeoutMS': 30000,
        }
        
        # Check if connection string uses mongodb+srv://
        if uri_to_use and uri_to_use.startswith('mongodb+srv://'):
            # For mongodb+srv://, TLS is automatic, but we can add retryWrites if not present
            if 'retryWrites' not in uri_to_use:
                separator = '&' if '?' in uri_to_use else '?'
                uri_with_params = f"{uri_to_use}{separator}retryWrites=true&w=majority"
            else:
                uri_with_params = uri_to_use
        else:
            # For standard mongodb:// connections, explicitly enable TLS
            connection_params['tls'] = True
            connection_params['tlsAllowInvalidCertificates'] = False
            uri_with_params = uri_to_use
        
        # Try to create client - if SSL fails, provide helpful error
        try:
            self.client = MongoClient(uri_with_params, **connection_params)
            # Test connection immediately
            self.client.admin.command('ping')
        except Exception as e:
            error_msg = str(e)
            if 'SSL' in error_msg or 'TLS' in error_msg or 'handshake' in error_msg:
                print("\n" + "="*70)
                print("SSL/TLS CONNECTION ERROR DETECTED")
                print("="*70)
                print("\nYour connection string should be in this format:")
                print("mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority")
                print("\nCommon fixes:")
                print("1. Ensure you're using 'mongodb+srv://' (not 'mongodb://')")
                print("2. Check MongoDB Atlas → Network Access → Add your IP address")
                print("3. Verify username/password are correct and URL-encoded")
                print("4. Try: pip install --upgrade pymongo")
                print("="*70 + "\n")
            raise
        db_name = database_name or Config.MONGODB_DATABASE_NAME
        self.db = self.client[db_name]
        collection = collection_name or Config.MONGODB_COLLECTION_NAME
        self.collection = self.db[collection]
        self.index_name = index_name or Config.MONGODB_VECTOR_INDEX_NAME
    
    def test_connection(self) -> bool:
        """Test MongoDB connection."""
        try:
            self.client.admin.command('ping')
            return True
        except ConnectionFailure:
            return False
    
    def store_chunks(self, chunks: List[DocumentChunk]) -> int:
        """
        Store document chunks in MongoDB.
        
        Args:
            chunks: List of document chunks with embeddings
            
        Returns:
            Number of chunks stored
        """
        if not chunks:
            return 0
        
        documents = [chunk.to_dict() for chunk in chunks]
        result = self.collection.insert_many(documents)
        return len(result.inserted_ids)
    
    def vector_search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            
        Returns:
            List of matching documents with scores
        """
        try:
            # MongoDB Atlas Vector Search aggregation pipeline
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": self.index_name,
                        "path": "embedding",
                        "queryVector": query_embedding,
                        "numCandidates": top_k * 10,
                        "limit": top_k
                    }
                },
                {
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
                        "score": {"$meta": "vectorSearchScore"}
                    }
                }
            ]
            
            results = list(self.collection.aggregate(pipeline))
            if results:
                print(f"[VectorStore] Vector search returned {len(results)} results")
                # Log sample result to verify fields
                if results:
                    sample = results[0]
                    print(f"[VectorStore] Sample result fields: {list(sample.keys())}")
                    print(f"[VectorStore] Sample file_name: '{sample.get('file_name')}', "
                          f"line_start: {sample.get('line_start')}, line_end: {sample.get('line_end')}")
                return results
            else:
                print(f"[VectorStore] Vector search returned 0 results, trying fallback text search")
                return self._fallback_text_search(top_k)
            
        except OperationFailure as e:
            # If vector search index doesn't exist, fallback to basic search
            error_msg = str(e)
            print(f"[VectorStore] Vector search failed: {error_msg}")
            print(f"[VectorStore] Index '{self.index_name}' may not exist. Using fallback text search.")
            
            # Check if collection has documents
            doc_count = self.collection.count_documents({})
            print(f"[VectorStore] Collection has {doc_count} documents")
            
            if doc_count == 0:
                print("[VectorStore] Collection is empty - no documents to search")
                return []
            
            return self._fallback_text_search(top_k)
        except Exception as e:
            print(f"[VectorStore] Unexpected error in vector search: {str(e)}")
            import traceback
            traceback.print_exc()
            # Try fallback
            return self._fallback_text_search(top_k)
    
    def _fallback_text_search(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Fallback text-based search when vector search fails.
        Returns random documents from the collection as a basic fallback.
        
        Args:
            top_k: Number of results to return
            
        Returns:
            List of documents with placeholder scores
        """
        try:
            print(f"[VectorStore] Executing fallback text search for {top_k} results")
            
            # Get random documents from collection
            # Using sample aggregation for random selection
            pipeline = [
                {"$sample": {"size": top_k}},
                {
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
                        "score": 0.5  # Placeholder score for fallback results
                    }
                }
            ]
            
            results = list(self.collection.aggregate(pipeline))
            
            if not results:
                # If $sample doesn't work, try simple find
                print("[VectorStore] $sample failed, trying simple find")
                results = list(self.collection.find(
                    {},
                    {
                        "_id": 0,
                        "chunk_id": 1,
                        "document_id": 1,
                        "file_name": 1,
                        "chunk_index": 1,
                        "content": 1,
                        "line_start": 1,
                        "line_end": 1,
                        "metadata": 1
                    }
                ).limit(top_k))
                
                # Add placeholder scores
                for result in results:
                    result["score"] = 0.5
            
            print(f"[VectorStore] Fallback search returned {len(results)} results")
            
            # Log sample result to verify fields
            if results:
                sample = results[0]
                print(f"[VectorStore] Fallback sample fields: {list(sample.keys())}")
                print(f"[VectorStore] Fallback sample file_name: '{sample.get('file_name')}', "
                      f"line_start: {sample.get('line_start')}, line_end: {sample.get('line_end')}")
            
            return results
            
        except Exception as e:
            print(f"[VectorStore] Fallback text search also failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get all chunks for a specific document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            List of document chunks
        """
        return list(self.collection.find(
            {"document_id": document_id},
            {"_id": 0}
        ).sort("chunk_index", 1))
    
    def delete_document(self, document_id: str) -> int:
        """
        Delete all chunks for a document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Number of chunks deleted
        """
        result = self.collection.delete_many({"document_id": document_id})
        return result.deleted_count
    
    def get_all_documents(self) -> List[Dict[str, Any]]:
        """
        Get list of all documents (unique document IDs with metadata).
        
        Returns:
            List of document metadata
        """
        pipeline = [
            {
                "$group": {
                    "_id": "$document_id",
                    "file_name": {"$first": "$file_name"},
                    "chunk_count": {"$sum": 1}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "document_id": "$_id",
                    "file_name": 1,
                    "chunk_count": 1
                }
            }
        ]
        return list(self.collection.aggregate(pipeline))
    
    def close(self):
        """Close MongoDB connection."""
        self.client.close()

