"""Qdrant origin source implementation."""

from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import ScrollRequest

from backend.services.origin_sources.base import OriginSource
from backend.models.origin_source import OriginDocument


class QdrantOrigin(OriginSource):
    """Qdrant collection as origin source."""
    
    def __init__(self, source_id: str, connection_config: Dict[str, Any], **kwargs):
        """
        Initialize Qdrant origin source.
        
        Args:
            source_id: Source identifier
            connection_config: Must contain 'uri', optionally 'api_key', 'collection_name'
            **kwargs: Additional parameters
        """
        super().__init__(source_id, connection_config)
        self.uri = connection_config.get('uri')
        self.api_key = connection_config.get('api_key')
        self.collection_name = connection_config.get('collection_name') or kwargs.get('collection_name', 'documents')
        
        if not self.uri:
            raise ValueError("Qdrant URI is required in connection_config")
        
        self.client = None
        self._connect()
    
    def _connect(self):
        """Connect to Qdrant."""
        try:
            if self.api_key:
                self.client = QdrantClient(url=self.uri, api_key=self.api_key)
            else:
                self.client = QdrantClient(url=self.uri)
        except Exception as e:
            print(f"[QdrantOrigin] Error connecting: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test Qdrant connection."""
        try:
            if not self.client:
                self._connect()
            self.client.get_collections()
            return True
        except Exception:
            return False
    
    def list_documents(self, limit: int = 100, skip: int = 0) -> List[OriginDocument]:
        """List documents from Qdrant collection."""
        try:
            if not self.client:
                self._connect()
            
            # Scroll through points in collection
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                limit=limit,
                offset=skip,
                with_payload=True
            )
            
            documents = []
            for point in scroll_result[0]:  # scroll_result is (points, next_page_offset)
                payload = point.payload or {}
                
                # Extract content from payload
                content = payload.get('content') or payload.get('text') or str(payload)
                
                origin_doc = OriginDocument(
                    origin_id=str(point.id),
                    title=payload.get('title') or payload.get('file_name'),
                    content_preview=str(content)[:200] if content else None,
                    metadata={k: v for k, v in payload.items() if k not in ['content', 'text']},
                    size=len(str(content)) if content else None
                )
                documents.append(origin_doc)
            
            return documents
        except Exception as e:
            print(f"[QdrantOrigin] Error listing documents: {e}")
            return []
    
    def get_document(self, origin_id: str) -> Optional[Dict[str, Any]]:
        """Get full document from Qdrant."""
        try:
            if not self.client:
                self._connect()
            
            # Retrieve point by ID
            try:
                point_id = int(origin_id)
            except:
                point_id = hash(origin_id) % (2**63)
            
            points = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[point_id],
                with_payload=True
            )
            
            if not points:
                return None
            
            point = points[0]
            payload = point.payload or {}
            
            # Extract content
            content = payload.get('content') or payload.get('text') or str(payload)
            
            return {
                'origin_id': str(point.id),
                'content': str(content),
                'metadata': {k: v for k, v in payload.items() if k not in ['content', 'text']}
            }
        except Exception as e:
            print(f"[QdrantOrigin] Error getting document: {e}")
            return None
    
    def close(self):
        """Close Qdrant connection."""
        # Qdrant client doesn't need explicit close
        pass

