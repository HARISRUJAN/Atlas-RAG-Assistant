"""Query request and response models."""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class SourceReference:
    """Source reference for RAG responses."""
    
    file_name: str
    line_start: int
    line_end: int
    content: str
    relevance_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'file_name': self.file_name,
            'line_start': self.line_start,
            'line_end': self.line_end,
            'content': self.content,
            'relevance_score': round(self.relevance_score, 4)
        }


@dataclass
class QueryRequest:
    """Query request model."""
    
    query: str
    top_k: int = 5
    collection_name: str = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueryRequest':
        """Create from dictionary."""
        return cls(
            query=data.get('query', ''),
            top_k=data.get('top_k', 5),
            collection_name=data.get('collection_name')
        )


@dataclass
class QueryResponse:
    """Query response model."""
    
    answer: str
    sources: List[SourceReference]
    query: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'answer': self.answer,
            'sources': [source.to_dict() for source in self.sources],
            'query': self.query
        }

