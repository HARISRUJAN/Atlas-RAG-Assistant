"""File system origin source implementation."""

from typing import List, Dict, Any, Optional
import os
from pathlib import Path

from backend.services.origin_sources.base import OriginSource
from backend.models.origin_source import OriginDocument


class FilesystemOrigin(OriginSource):
    """File system directory as origin source."""
    
    def __init__(self, source_id: str, connection_config: Dict[str, Any], **kwargs):
        """
        Initialize filesystem origin source.
        
        Args:
            source_id: Source identifier
            connection_config: Must contain 'base_path' (directory path)
            **kwargs: Additional parameters
        """
        super().__init__(source_id, connection_config)
        self.base_path = connection_config.get('base_path') or kwargs.get('base_path')
        
        if not self.base_path:
            raise ValueError("base_path is required in connection_config")
        
        self.base_path = Path(self.base_path)
        if not self.base_path.exists():
            raise ValueError(f"Path does not exist: {self.base_path}")
        if not self.base_path.is_dir():
            raise ValueError(f"Path is not a directory: {self.base_path}")
    
    def test_connection(self) -> bool:
        """Test filesystem access."""
        try:
            return self.base_path.exists() and self.base_path.is_dir()
        except Exception:
            return False
    
    def list_documents(self, limit: int = 100, skip: int = 0) -> List[OriginDocument]:
        """List files in the directory."""
        try:
            # Supported file extensions
            supported_extensions = {'.txt', '.md', '.pdf', '.docx', '.json'}
            
            files = []
            for file_path in self.base_path.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                    files.append(file_path)
            
            # Sort by name
            files.sort(key=lambda p: p.name)
            
            # Apply skip and limit
            files = files[skip:skip + limit]
            
            documents = []
            for file_path in files:
                try:
                    # Get relative path as origin_id
                    origin_id = str(file_path.relative_to(self.base_path))
                    
                    # Get file size
                    size = file_path.stat().st_size
                    
                    # Try to read preview
                    content_preview = None
                    if file_path.suffix.lower() in {'.txt', '.md'}:
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content_preview = f.read(200)
                        except:
                            pass
                    
                    origin_doc = OriginDocument(
                        origin_id=origin_id,
                        title=file_path.name,
                        content_preview=content_preview,
                        metadata={
                            'file_path': str(file_path),
                            'file_size': size,
                            'file_extension': file_path.suffix
                        },
                        size=size
                    )
                    documents.append(origin_doc)
                except Exception as e:
                    print(f"[FilesystemOrigin] Error processing file {file_path}: {e}")
                    continue
            
            return documents
        except Exception as e:
            print(f"[FilesystemOrigin] Error listing documents: {e}")
            return []
    
    def get_document(self, origin_id: str) -> Optional[Dict[str, Any]]:
        """Get file content from filesystem."""
        try:
            file_path = self.base_path / origin_id
            
            if not file_path.exists() or not file_path.is_file():
                return None
            
            # Read file content based on extension
            content = None
            if file_path.suffix.lower() in {'.txt', '.md'}:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            elif file_path.suffix.lower() == '.json':
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    content = json.dumps(data, indent=2)
            else:
                # For binary files, return path reference
                content = f"Binary file: {file_path.name}"
            
            return {
                'origin_id': origin_id,
                'content': content or '',
                'metadata': {
                    'file_path': str(file_path),
                    'file_size': file_path.stat().st_size,
                    'file_extension': file_path.suffix
                }
            }
        except Exception as e:
            print(f"[FilesystemOrigin] Error getting document: {e}")
            return None
    
    def close(self):
        """Close filesystem connection (no-op)."""
        pass

