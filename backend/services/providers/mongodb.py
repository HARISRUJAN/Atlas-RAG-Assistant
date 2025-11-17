"""MongoDB provider for vector store."""

from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

from backend.services.providers.base import VectorStoreProvider
from backend.services.vector_store import VectorStoreService
from backend.models.document import DocumentChunk


class MongoDBProvider(VectorStoreProvider):
    """MongoDB vector store provider."""
    
    def __init__(self, uri: str, api_key: Optional[str] = None, **kwargs):
        """
        Initialize MongoDB provider.
        
        Args:
            uri: MongoDB connection URI
            api_key: Not used for MongoDB (included for interface compatibility)
            **kwargs: Additional parameters (database_name, collection_name, index_name)
        """
        super().__init__(uri, api_key)
        self.database_name = kwargs.get('database_name')
        self.collection_name = kwargs.get('collection_name')
        self.index_name = kwargs.get('index_name')
        self.client = None
        self.vector_store = None
    
    def _get_vector_store(self, collection_name: Optional[str] = None) -> VectorStoreService:
        """Get or create vector store service."""
        coll_name = collection_name or self.collection_name
        return VectorStoreService(
            collection_name=coll_name,
            database_name=self.database_name,
            index_name=self.index_name,
            mongodb_uri=self.uri
        )
    
    def test_connection(self) -> bool:
        """Test MongoDB connection."""
        try:
            client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            client.close()
            return True
        except (ConnectionFailure, Exception):
            return False
    
    def list_collections(self) -> List[str]:
        """List MongoDB databases and collections."""
        try:
            client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            
            # Get all databases
            database_names = client.list_database_names()
            system_databases = {'admin', 'local', 'config'}
            filtered_databases = [name for name in database_names if name not in system_databases]
            
            collections = []
            for db_name in filtered_databases:
                db = client[db_name]
                collection_names = db.list_collection_names()
                filtered_collections = [
                    name for name in collection_names 
                    if not name.startswith('system.')
                ]
                for coll_name in filtered_collections:
                    collections.append(f"{db_name}.{coll_name}")
            
            client.close()
            return collections
        except Exception as e:
            print(f"Error listing MongoDB collections: {e}")
            return []
    
    def vector_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        collection_name: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Perform vector search in MongoDB."""
        try:
            print(f"[MongoDBProvider] Starting vector search (collection: {collection_name}, top_k: {top_k})")
            vector_store = self._get_vector_store(collection_name)
            
            # Validate collection has documents
            doc_count = vector_store.collection.count_documents({})
            print(f"[MongoDBProvider] Collection has {doc_count} documents")
            
            if doc_count == 0:
                print(f"[MongoDBProvider] WARNING: Collection is empty")
                vector_store.close()
                return []
            
            results = vector_store.vector_search(query_embedding, top_k)
            print(f"[MongoDBProvider] Vector search returned {len(results)} results")
            vector_store.close()
            return results
        except Exception as e:
            error_msg = f"Error in MongoDB vector search: {str(e)}"
            print(f"[MongoDBProvider] ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            return []
    
    def store_chunks(
        self,
        chunks: List[DocumentChunk],
        collection_name: Optional[str] = None,
        **kwargs
    ) -> int:
        """Store chunks in MongoDB."""
        try:
            vector_store = self._get_vector_store(collection_name)
            count = vector_store.store_chunks(chunks)
            vector_store.close()
            return count
        except Exception as e:
            print(f"Error storing chunks in MongoDB: {e}")
            return 0
    
    def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()

