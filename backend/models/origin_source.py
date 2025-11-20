"""Origin source data model for pluggable data sources."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


@dataclass
class OriginSource:
    """
    Model for managing pluggable origin data sources.
    
    Origin sources are where data originates before being ingested into
    the raw_documents collection. Examples: MongoDB collections, Qdrant,
    filesystem, external APIs, etc.
    """
    
    source_id: str
    source_type: str  # 'mongodb', 'qdrant', 'filesystem', 'file_upload', 'api', etc.
    display_name: str
    connection_config: Dict[str, Any]  # Connection details (URI, credentials, etc.)
    collection_name: Optional[str] = None  # For MongoDB/Qdrant: collection/index name
    database_name: Optional[str] = None  # For MongoDB: database name
    status: str = 'active'  # 'active', 'inactive', 'error'
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_sync_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'source_id': self.source_id,
            'source_type': self.source_type,
            'display_name': self.display_name,
            'connection_config': self.connection_config,
            'collection_name': self.collection_name,
            'database_name': self.database_name,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OriginSource':
        """Create OriginSource from dictionary."""
        return cls(
            source_id=data.get('source_id', str(uuid.uuid4())),
            source_type=data['source_type'],
            display_name=data['display_name'],
            connection_config=data['connection_config'],
            collection_name=data.get('collection_name'),
            database_name=data.get('database_name'),
            status=data.get('status', 'active'),
            created_at=datetime.fromisoformat(data['created_at']) if isinstance(data.get('created_at'), str) else data.get('created_at', datetime.utcnow()),
            last_sync_at=datetime.fromisoformat(data['last_sync_at']) if isinstance(data.get('last_sync_at'), str) and data.get('last_sync_at') else None,
            metadata=data.get('metadata', {})
        )


@dataclass
class OriginDocument:
    """
    Represents a document from an origin source before ingestion.
    
    This is a lightweight representation used when browsing origin sources.
    """
    
    origin_id: str  # ID in the origin source
    title: Optional[str] = None
    content_preview: Optional[str] = None  # First N characters
    metadata: Dict[str, Any] = field(default_factory=dict)
    size: Optional[int] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'origin_id': self.origin_id,
            'title': self.title,
            'content_preview': self.content_preview,
            'metadata': self.metadata,
            'size': self.size,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

