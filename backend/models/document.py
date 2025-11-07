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
    
    def to_dict(self):
        """Convert to dictionary for MongoDB storage."""
        return {
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

