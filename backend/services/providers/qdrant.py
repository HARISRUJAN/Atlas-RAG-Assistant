"""Qdrant provider for vector store."""

from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
try:
    from qdrant_client.models import Distance, VectorParams, Point, Filter, FieldCondition, MatchValue
except ImportError:
    # Try alternative import for newer versions
    from qdrant_client.models import Distance, VectorParams, Filter, FieldCondition, MatchValue
    try:
        from qdrant_client.models import PointStruct as Point
    except ImportError:
        # Fallback - we'll construct points differently
        Point = None

from backend.services.providers.base import VectorStoreProvider
from backend.models.document import DocumentChunk


class QdrantProvider(VectorStoreProvider):
    """Qdrant vector store provider."""
    
    def __init__(self, uri: str, api_key: Optional[str] = None, **kwargs):
        """
        Initialize Qdrant provider.
        
        Args:
            uri: Qdrant server URL
            api_key: Qdrant API key (if required)
            **kwargs: Additional parameters
        """
        super().__init__(uri, api_key)
        self.client = None
    
    def _get_client(self) -> QdrantClient:
        """Get or create Qdrant client."""
        if self.client is None:
            if self.api_key:
                self.client = QdrantClient(url=self.uri, api_key=self.api_key)
            else:
                self.client = QdrantClient(url=self.uri)
        return self.client
    
    def test_connection(self) -> bool:
        """Test Qdrant connection."""
        try:
            client = self._get_client()
            client.get_collections()
            return True
        except Exception:
            return False
    
    def list_collections(self) -> List[str]:
        """List Qdrant collections."""
        try:
            client = self._get_client()
            collections = client.get_collections()
            return [coll.name for coll in collections.collections]
        except Exception as e:
            print(f"Error listing Qdrant collections: {e}")
            return []
    
    def vector_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        collection_name: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Perform vector search in Qdrant."""
        try:
            client = self._get_client()
            
            if not collection_name:
                # Use first available collection
                collections = client.get_collections()
                if not collections.collections:
                    print("Warning: No collections found in Qdrant")
                    return []
                collection_name = collections.collections[0].name
                print(f"Using default collection: {collection_name}")
            
            # Verify collection exists and get its config
            try:
                collection_info = client.get_collection(collection_name)
                vector_size = collection_info.config.params.vectors.size
                if len(query_embedding) != vector_size:
                    print(f"Warning: Query embedding dimension ({len(query_embedding)}) doesn't match collection vector size ({vector_size})")
            except Exception as e:
                print(f"Warning: Could not verify collection {collection_name}: {e}")
            
            # Search
            results = client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=top_k
            )
            
            # Format results
            formatted_results = []
            for result in results:
                payload = result.payload or {}
                # Ensure score is a float (Qdrant returns float, but handle None)
                score = float(result.score) if result.score is not None else 0.0
                
                # Handle empty strings - use 'Unknown' for missing file_name
                file_name = payload.get('file_name', '') or 'Unknown'
                if isinstance(file_name, str) and file_name.strip() == '':
                    file_name = 'Unknown'
                
                formatted_results.append({
                    'chunk_id': payload.get('chunk_id', ''),
                    'document_id': payload.get('document_id', ''),
                    'file_name': file_name,
                    'content': payload.get('content', ''),
                    'line_start': int(payload.get('line_start', 0)) if payload.get('line_start') else 0,
                    'line_end': int(payload.get('line_end', 0)) if payload.get('line_end') else 0,
                    'metadata': payload.get('metadata', {}),
                    'score': score
                })
            
            return formatted_results
        except Exception as e:
            import traceback
            error_msg = f"Error in Qdrant vector search: {e}"
            print(error_msg)
            traceback.print_exc()
            # Return empty list instead of raising to prevent breaking the query
            # The error will be logged above
            return []
    
    def store_chunks(
        self,
        chunks: List[DocumentChunk],
        collection_name: Optional[str] = None,
        **kwargs
    ) -> int:
        """Store chunks in Qdrant."""
        try:
            client = self._get_client()
            
            if not collection_name:
                collection_name = "documents"
            
            # Ensure collection exists
            self._ensure_collection(client, collection_name, len(chunks[0].embedding) if chunks else 384)
            
            # Prepare points
            points = []
            for chunk in chunks:
                if Point:
                    point = Point(
                        id=hash(chunk.chunk_id) % (2**63),  # Convert to int64
                        vector=chunk.embedding,
                        payload={
                            'chunk_id': chunk.chunk_id,
                            'document_id': chunk.document_id,
                            'file_name': chunk.file_name,
                            'content': chunk.content,
                            'line_start': chunk.line_start,
                            'line_end': chunk.line_end,
                            'metadata': chunk.metadata or {}
                        }
                    )
                else:
                    # Fallback: use dict format
                    point = {
                        'id': hash(chunk.chunk_id) % (2**63),
                        'vector': chunk.embedding,
                        'payload': {
                            'chunk_id': chunk.chunk_id,
                            'document_id': chunk.document_id,
                            'file_name': chunk.file_name,
                            'content': chunk.content,
                            'line_start': chunk.line_start,
                            'line_end': chunk.line_end,
                            'metadata': chunk.metadata or {}
                        }
                    }
                points.append(point)
            
            # Upsert points
            client.upsert(collection_name=collection_name, points=points)
            
            return len(points)
        except Exception as e:
            print(f"Error storing chunks in Qdrant: {e}")
            return 0
    
    def _ensure_collection(self, client: QdrantClient, collection_name: str, vector_size: int = 384):
        """Ensure collection exists."""
        try:
            client.get_collection(collection_name)
        except:
            # Create collection
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )
    
    def close(self):
        """Close Qdrant connection."""
        # Qdrant client doesn't need explicit close
        pass

