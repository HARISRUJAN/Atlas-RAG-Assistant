"""Base class for vector store providers."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from backend.models.document import DocumentChunk


class VectorStoreProvider(ABC):
    """Abstract base class for vector store providers."""
    
    def __init__(self, uri: str, api_key: Optional[str] = None, **kwargs):
        """
        Initialize provider.
        
        Args:
            uri: Connection URI/URL
            api_key: Optional API key
            **kwargs: Additional provider-specific parameters
        """
        self.uri = uri
        self.api_key = api_key
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test connection to vector store.
        
        Returns:
            True if connection is successful
        """
        pass
    
    @abstractmethod
    def list_collections(self) -> List[str]:
        """
        List available collections/indexes.
        
        Returns:
            List of collection/index names
        """
        pass
    
    @abstractmethod
    def vector_search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        collection_name: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            collection_name: Optional collection/index name
            **kwargs: Additional search parameters
            
        Returns:
            List of matching documents with scores
        """
        pass
    
    @abstractmethod
    def store_chunks(
        self,
        chunks: List[DocumentChunk],
        collection_name: Optional[str] = None,
        **kwargs
    ) -> int:
        """
        Store document chunks.
        
        Args:
            chunks: List of document chunks with embeddings
            collection_name: Optional collection/index name
            **kwargs: Additional storage parameters
            
        Returns:
            Number of chunks stored
        """
        pass
    
    def close(self):
        """Close connection (override if needed)."""
        pass

