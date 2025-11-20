"""Base class for pluggable origin sources."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from backend.models.origin_source import OriginDocument


class OriginSource(ABC):
    """Abstract base class for origin data sources."""
    
    def __init__(self, source_id: str, connection_config: Dict[str, Any], **kwargs):
        """
        Initialize origin source.
        
        Args:
            source_id: Unique identifier for this source
            connection_config: Connection configuration (URI, credentials, etc.)
            **kwargs: Additional source-specific parameters
        """
        self.source_id = source_id
        self.connection_config = connection_config
    
    @abstractmethod
    def list_documents(self, limit: int = 100, skip: int = 0) -> List[OriginDocument]:
        """
        List documents available in the origin source.
        
        Args:
            limit: Maximum number of documents to return
            skip: Number of documents to skip
            
        Returns:
            List of OriginDocument instances
        """
        pass
    
    @abstractmethod
    def get_document(self, origin_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full document content from origin source.
        
        Args:
            origin_id: Document ID in the origin source
            
        Returns:
            Dictionary with document data including 'content' field, or None if not found
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test connection to origin source.
        
        Returns:
            True if connection is successful
        """
        pass
    
    def get_source_type(self) -> str:
        """Get the source type identifier."""
        return self.__class__.__name__.replace('Origin', '').lower()

