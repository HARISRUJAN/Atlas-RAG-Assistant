"""Document data models."""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class DocumentMetadata:
    """Metadata for uploaded documents."""
    
    document_id: str
    file_name: str
    file_type: str
    file_size: int
    upload_date: datetime
    total_chunks: int
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'document_id': self.document_id,
            'file_name': self.file_name,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'upload_date': self.upload_date.isoformat(),
            'total_chunks': self.total_chunks
        }


@dataclass
class DocumentChunk:
    """Individual document chunk with embeddings."""
    
    chunk_id: str
    document_id: str
    file_name: str
    chunk_index: int
    content: str
    line_start: int
    line_end: int
    embedding: Optional[List[float]] = None
    metadata: Optional[dict] = None
    origin_id: Optional[str] = None  # Reference to origin document ID
    raw_document_id: Optional[str] = None  # Reference to raw_document_id in raw_documents collection
    
    def to_dict(self):
        """Convert to dictionary for MongoDB storage."""
        result = {
            'chunk_id': self.chunk_id,
            'document_id': self.document_id,
            'file_name': self.file_name,
            'chunk_index': self.chunk_index,
            'content': self.content,
            'line_start': self.line_start,
            'line_end': self.line_end,
            'embedding': self.embedding,
            'metadata': self.metadata or {}
        }
        # Add origin references if available
        if self.origin_id:
            result['origin_id'] = self.origin_id
        if self.raw_document_id:
            result['raw_document_id'] = self.raw_document_id
        return result

