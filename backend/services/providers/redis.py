"""Redis provider for vector store."""

from typing import List, Dict, Any, Optional
import redis
try:
    from redis.commands.search.field import VectorField, TextField
    from redis.commands.search.indexDefinition import IndexDefinition, IndexType
    from redis.commands.search.query import Query
    REDIS_SEARCH_AVAILABLE = True
except ImportError:
    # Redis Stack/RediSearch not available - provide fallback
    REDIS_SEARCH_AVAILABLE = False
    VectorField = None
    TextField = None
    IndexDefinition = None
    IndexType = None
    Query = None

from backend.services.providers.base import VectorStoreProvider
from backend.models.document import DocumentChunk


class RedisProvider(VectorStoreProvider):
    """Redis with RediSearch vector store provider."""
    
    def __init__(self, uri: str, api_key: Optional[str] = None, **kwargs):
        """
        Initialize Redis provider.
        
        Args:
            uri: Redis connection URI (redis://:password@host:port/db)
            api_key: Not used for Redis (included for interface compatibility)
            **kwargs: Additional parameters (index_name)
        """
        super().__init__(uri, api_key)
        self.index_name = kwargs.get('index_name', 'vector_index')
        self.client = None
    
    def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self.client is None:
            self.client = redis.from_url(self.uri, decode_responses=False)
        return self.client
    
    def test_connection(self) -> bool:
        """Test Redis connection."""
        try:
            if not REDIS_SEARCH_AVAILABLE:
                print("[RedisProvider] RediSearch not available")
                return False
            client = self._get_client()
            client.ping()
            return True
        except Exception as e:
            print(f"[RedisProvider] Connection test failed: {e}")
            return False
    
    def list_collections(self) -> List[str]:
        """List Redis indexes (collections)."""
        try:
            if not REDIS_SEARCH_AVAILABLE:
                return []
            client = self._get_client()
            # List all indexes
            indexes = []
            try:
                info = client.ft(self.index_name).info()
                indexes.append(self.index_name)
            except Exception as e:
                print(f"[RedisProvider] Index '{self.index_name}' not found or error accessing: {e}")
            # In Redis, we typically use one index, but can have multiple
            return indexes if indexes else [self.index_name]
        except Exception as e:
            print(f"[RedisProvider] Error listing Redis indexes: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def vector_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        collection_name: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Perform vector search in Redis."""
        try:
            if not REDIS_SEARCH_AVAILABLE:
                return []
            client = self._get_client()
            index_name = collection_name or self.index_name
            
            # Create query
            query = Query(f"*=>[KNN {top_k} @embedding $vec]").return_fields(
                "chunk_id", "document_id", "file_name", "content", 
                "line_start", "line_end", "metadata"
            ).dialect(2)
            
            # Execute search
            results = client.ft(index_name).search(
                query, 
                query_params={"vec": query_embedding}
            )
            
            # Format results
            formatted_results = []
            for doc in results.docs:
                # Handle empty strings - use 'Unknown' for missing file_name
                file_name = doc.get('file_name', '') or 'Unknown'
                if isinstance(file_name, str) and file_name.strip() == '':
                    file_name = 'Unknown'
                
                formatted_result = {
                    'chunk_id': doc.get('chunk_id', ''),
                    'document_id': doc.get('document_id', ''),
                    'file_name': file_name,
                    'content': doc.get('content', ''),
                    'line_start': int(doc.get('line_start', 0)) if doc.get('line_start') else 0,
                    'line_end': int(doc.get('line_end', 0)) if doc.get('line_end') else 0,
                    'metadata': doc.get('metadata', {}),
                    'score': float(doc.get('__vector_score', 0.0)) if doc.get('__vector_score') else 0.0
                }
                formatted_results.append(formatted_result)
            
            # Log field extraction details
            if formatted_results:
                print(f"[RedisProvider] Returned {len(formatted_results)} results")
                sample = formatted_results[0]
                print(f"[RedisProvider] Sample result - file_name: '{sample.get('file_name')}', "
                      f"line_start: {sample.get('line_start')}, line_end: {sample.get('line_end')}, "
                      f"content_length: {len(sample.get('content', ''))}, score: {sample.get('score')}")
            
            return formatted_results
        except Exception as e:
            error_msg = f"Error in Redis vector search: {str(e)}"
            print(f"[RedisProvider] ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            return []
    
    def store_chunks(
        self,
        chunks: List[DocumentChunk],
        collection_name: Optional[str] = None,
        **kwargs
    ) -> int:
        """Store chunks in Redis."""
        try:
            if not REDIS_SEARCH_AVAILABLE:
                print("[RedisProvider] RediSearch not available, cannot store chunks")
                return 0
            
            if not chunks:
                print(f"[RedisProvider] No chunks to store")
                return 0
            
            client = self._get_client()
            index_name = collection_name or self.index_name
            
            # Ensure index exists
            self._ensure_index(client, index_name)
            
            stored = 0
            for chunk in chunks:
                key = f"{index_name}:{chunk.chunk_id}"
                data = {
                    'chunk_id': chunk.chunk_id,
                    'document_id': chunk.document_id,
                    'file_name': chunk.file_name,
                    'content': chunk.content,
                    'line_start': chunk.line_start,
                    'line_end': chunk.line_end,
                    'embedding': chunk.embedding,
                    'metadata': str(chunk.metadata) if chunk.metadata else ''
                }
                client.hset(key, mapping=data)
                stored += 1
            
            print(f"[RedisProvider] Stored {stored} chunks in Redis")
            return stored
        except Exception as e:
            error_msg = f"Error storing chunks in Redis: {str(e)}"
            print(f"[RedisProvider] ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            return 0
    
    def _ensure_index(self, client: redis.Redis, index_name: str):
        """Ensure vector index exists."""
        if not REDIS_SEARCH_AVAILABLE:
            return
        try:
            client.ft(index_name).info()
        except:
            # Create index
            schema = (
                VectorField("embedding", "HNSW", {
                    "TYPE": "FLOAT32",
                    "DIM": 384,  # Default embedding dimension
                    "DISTANCE_METRIC": "COSINE"
                }),
                TextField("chunk_id"),
                TextField("document_id"),
                TextField("file_name"),
                TextField("content"),
            )
            client.ft(index_name).create_index(
                schema,
                definition=IndexDefinition(prefix=[f"{index_name}:"], index_type=IndexType.HASH)
            )
    
    def close(self):
        """Close Redis connection."""
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                print(f"[RedisProvider] Error closing client: {e}")
            finally:
                self.client = None

