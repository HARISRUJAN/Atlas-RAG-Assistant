"""Origin source factory and implementations."""

from typing import Dict, Any
from backend.services.origin_sources.base import OriginSource
from backend.services.origin_sources.mongodb_origin import MongoDBOrigin
from backend.services.origin_sources.qdrant_origin import QdrantOrigin
from backend.services.origin_sources.filesystem_origin import FilesystemOrigin


def create_origin_source(source_type: str, source_id: str, connection_config: Dict[str, Any], **kwargs) -> OriginSource:
    """
    Factory function to create origin source instances.
    
    Args:
        source_type: Type of origin source ('mongodb', 'qdrant', 'filesystem')
        source_id: Unique identifier for the source
        connection_config: Connection configuration dictionary
        **kwargs: Additional source-specific parameters
        
    Returns:
        OriginSource instance
        
    Raises:
        ValueError: If source_type is not supported
    """
    source_type_lower = source_type.lower()
    
    if source_type_lower == 'mongodb':
        return MongoDBOrigin(source_id, connection_config, **kwargs)
    elif source_type_lower == 'qdrant':
        return QdrantOrigin(source_id, connection_config, **kwargs)
    elif source_type_lower == 'filesystem':
        return FilesystemOrigin(source_id, connection_config, **kwargs)
    else:
        raise ValueError(f"Unsupported origin source type: {source_type}. Supported types: mongodb, qdrant, filesystem")


__all__ = [
    'OriginSource',
    'MongoDBOrigin',
    'QdrantOrigin',
    'FilesystemOrigin',
    'create_origin_source'
]

