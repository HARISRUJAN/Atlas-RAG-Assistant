"""Pinecone provider for vector store."""

from typing import List, Dict, Any, Optional
try:
    from pinecone import Pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    Pinecone = None
import uuid

from backend.services.providers.base import VectorStoreProvider
from backend.models.document import DocumentChunk


class PineconeProvider(VectorStoreProvider):
    """Pinecone vector store provider."""
    
    def __init__(self, uri: str, api_key: Optional[str] = None, **kwargs):
        """
        Initialize Pinecone provider.
        
        Args:
            uri: Pinecone controller URL (not used directly, but kept for interface)
            api_key: Pinecone API key (required)
            **kwargs: Additional parameters (environment, index_name)
        """
        super().__init__(uri, api_key)
        if not PINECONE_AVAILABLE:
            raise ValueError("Pinecone package not installed. Install with: pip install pinecone")
        if not api_key:
            raise ValueError("Pinecone requires an API key")
        self.environment = kwargs.get('environment', 'us-east-1')
        self.index_name = kwargs.get('index_name', 'documents')
        self.client = None
    
    def _get_client(self):
        """Get or create Pinecone client."""
        if not PINECONE_AVAILABLE:
            raise ValueError("Pinecone package not available")
        if self.client is None:
            self.client = Pinecone(api_key=self.api_key)
        return self.client
    
    def test_connection(self) -> bool:
        """Test Pinecone connection."""
        try:
            client = self._get_client()
            client.list_indexes()
            return True
        except Exception:
            return False
    
    def list_collections(self) -> List[str]:
        """List Pinecone indexes (collections)."""
        try:
            client = self._get_client()
            indexes = client.list_indexes()
            return [idx.name for idx in indexes.indexes]
        except Exception as e:
            print(f"Error listing Pinecone indexes: {e}")
            return []
    
    def vector_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        collection_name: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Perform vector search in Pinecone."""
        try:
            client = self._get_client()
            index_name = collection_name or self.index_name
            
            # Get index
            index = client.Index(index_name)
            
            # Search
            namespace = kwargs.get('namespace', '')
            results = index.query(
                vector=query_embedding,
                top_k=top_k,
                namespace=namespace,
                include_metadata=True
            )
            
            # Format results
            formatted_results = []
            for match in results.matches:
                metadata = match.metadata or {}
                # Handle empty strings - use 'Unknown' for missing file_name
                file_name = metadata.get('file_name', '') or 'Unknown'
                if isinstance(file_name, str) and file_name.strip() == '':
                    file_name = 'Unknown'
                
                formatted_results.append({
                    'chunk_id': metadata.get('chunk_id', ''),
                    'document_id': metadata.get('document_id', ''),
                    'file_name': file_name,
                    'content': metadata.get('content', ''),
                    'line_start': metadata.get('line_start', 0) or 0,
                    'line_end': metadata.get('line_end', 0) or 0,
                    'metadata': metadata.get('metadata', {}),
                    'score': match.score or 0.0
                })
            
            return formatted_results
        except Exception as e:
            print(f"Error in Pinecone vector search: {e}")
            return []
    
    def store_chunks(
        self,
        chunks: List[DocumentChunk],
        collection_name: Optional[str] = None,
        **kwargs
    ) -> int:
        """Store chunks in Pinecone."""
        try:
            client = self._get_client()
            index_name = collection_name or self.index_name
            namespace = kwargs.get('namespace', '')
            
            # Get index
            index = client.Index(index_name)
            
            # Prepare vectors
            vectors = []
            for chunk in chunks:
                vector_id = str(uuid.uuid4())
                vector_data = {
                    'id': vector_id,
                    'values': chunk.embedding,
                    'metadata': {
                        'chunk_id': chunk.chunk_id,
                        'document_id': chunk.document_id,
                        'file_name': chunk.file_name,
                        'content': chunk.content,
                        'line_start': chunk.line_start,
                        'line_end': chunk.line_end,
                        'metadata': chunk.metadata or {}
                    }
                }
                vectors.append(vector_data)
            
            # Upsert in batches
            batch_size = 100
            stored = 0
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                index.upsert(vectors=batch, namespace=namespace)
                stored += len(batch)
            
            return stored
        except Exception as e:
            print(f"Error storing chunks in Pinecone: {e}")
            return 0
    
    def close(self):
        """Close Pinecone connection."""
        # Pinecone client doesn't need explicit close
        pass

