"""Raw document data model for the two-stage pipeline."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
import uuid


@dataclass
class RawDocument:
    """
    Raw document model for storing unprocessed documents from origin sources.
    
    This represents the first stage of the pipeline where documents are stored
    exactly as received from origin sources before processing.
    """
    
    raw_document_id: str
    origin_id: str  # ID from the origin source
    origin_source_type: str  # 'mongodb', 'qdrant', 'filesystem', 'file_upload', etc.
    raw_content: str  # The raw document content (text, JSON, etc.)
    origin_source_id: Optional[str] = None  # Connection ID or source identifier
    content_type: str = 'text'  # 'text', 'json', 'binary', etc.
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    status: str = 'pending'  # 'pending', 'processing', 'processed', 'failed'
    created_at: datetime = field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        # Handle datetime serialization safely
        created_at_str = None
        if self.created_at:
            if isinstance(self.created_at, datetime):
                created_at_str = self.created_at.isoformat()
            else:
                created_at_str = str(self.created_at)
        
        processed_at_str = None
        if self.processed_at:
            if isinstance(self.processed_at, datetime):
                processed_at_str = self.processed_at.isoformat()
            else:
                processed_at_str = str(self.processed_at)
        
        return {
            'raw_document_id': self.raw_document_id,
            'origin_id': self.origin_id,
            'origin_source_type': self.origin_source_type,
            'origin_source_id': self.origin_source_id,
            'raw_content': self.raw_content,
            'content_type': self.content_type,
            'metadata': self.metadata,
            'status': self.status,
            'created_at': created_at_str,
            'processed_at': processed_at_str,
            'error_message': self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RawDocument':
        """Create RawDocument from dictionary."""
        # Handle created_at - can be datetime object (from MongoDB) or ISO string
        created_at = datetime.utcnow()
        if 'created_at' in data and data['created_at']:
            if isinstance(data['created_at'], datetime):
                created_at = data['created_at']
            elif isinstance(data['created_at'], str):
                try:
                    created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    created_at = datetime.utcnow()
        
        # Handle processed_at - can be datetime object, ISO string, or None
        processed_at = None
        if 'processed_at' in data and data['processed_at']:
            if isinstance(data['processed_at'], datetime):
                processed_at = data['processed_at']
            elif isinstance(data['processed_at'], str):
                try:
                    processed_at = datetime.fromisoformat(data['processed_at'].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    processed_at = None
        
        return cls(
            raw_document_id=data.get('raw_document_id', str(uuid.uuid4())),
            origin_id=data.get('origin_id', ''),
            origin_source_type=data.get('origin_source_type', 'unknown'),
            origin_source_id=data.get('origin_source_id'),
            raw_content=data.get('raw_content', ''),
            content_type=data.get('content_type', 'text'),
            metadata=data.get('metadata', {}),
            status=data.get('status', 'pending'),
            created_at=created_at,
            processed_at=processed_at,
            error_message=data.get('error_message')
        )
    
    def mark_processing(self):
        """Mark document as being processed."""
        self.status = 'processing'
    
    def mark_processed(self):
        """Mark document as processed."""
        self.status = 'processed'
        self.processed_at = datetime.utcnow()
    
    def mark_failed(self, error_message: str):
        """Mark document processing as failed."""
        self.status = 'failed'
        self.error_message = error_message

