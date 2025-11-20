"""MongoDB origin source implementation."""

from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from datetime import datetime

from backend.services.origin_sources.base import OriginSource
from backend.models.origin_source import OriginDocument


class MongoDBOrigin(OriginSource):
    """MongoDB collection as origin source."""
    
    def __init__(self, source_id: str, connection_config: Dict[str, Any], **kwargs):
        """
        Initialize MongoDB origin source.
        
        Args:
            source_id: Source identifier
            connection_config: Must contain 'uri', optionally 'database_name', 'collection_name'
            **kwargs: Additional parameters
        """
        super().__init__(source_id, connection_config)
        self.uri = connection_config.get('uri')
        self.database_name = connection_config.get('database_name') or kwargs.get('database_name')
        self.collection_name = connection_config.get('collection_name') or kwargs.get('collection_name')
        
        if not self.uri:
            raise ValueError("MongoDB URI is required in connection_config")
        if not self.database_name:
            raise ValueError("database_name is required")
        if not self.collection_name:
            raise ValueError("collection_name is required")
        
        self.client = None
        self._connect()
    
    def _connect(self):
        """Connect to MongoDB."""
        try:
            connection_params = {
                'serverSelectionTimeoutMS': 10000,
                'connectTimeoutMS': 10000,
            }
            
            if self.uri.startswith('mongodb+srv://'):
                if 'retryWrites' not in self.uri:
                    separator = '&' if '?' in self.uri else '?'
                    uri_with_params = f"{self.uri}{separator}retryWrites=true&w=majority"
                else:
                    uri_with_params = self.uri
            else:
                # Don't force TLS for non-SRV connections - let MongoDB URI handle it
                # Only add connection params if needed
                uri_with_params = self.uri
            
            print(f"[MongoDBOrigin] Connecting to: {self.uri[:50]}... (database: {self.database_name}, collection: {self.collection_name})")
            self.client = MongoClient(uri_with_params, **connection_params)
            
            # Test connection
            self.client.admin.command('ping')
            
            # Access database and collection
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            
            # Verify collection exists (this will not fail if collection doesn't exist, but we can check)
            if self.database_name not in self.client.list_database_names():
                print(f"[MongoDBOrigin] Warning: Database '{self.database_name}' not found in server")
            
            print(f"[MongoDBOrigin] Successfully connected to {self.database_name}.{self.collection_name}")
        except ConnectionFailure as e:
            error_msg = f"MongoDB connection failed: {str(e)}"
            print(f"[MongoDBOrigin] {error_msg}")
            raise ConnectionFailure(error_msg) from e
        except Exception as e:
            error_msg = f"Error connecting to MongoDB: {str(e)}"
            print(f"[MongoDBOrigin] {error_msg}")
            raise ValueError(error_msg) from e
    
    def test_connection(self) -> bool:
        """Test MongoDB connection."""
        try:
            if not self.client:
                self._connect()
            self.client.admin.command('ping')
            return True
        except Exception:
            return False
    
    def list_documents(self, limit: int = 100, skip: int = 0) -> List[OriginDocument]:
        """List documents from MongoDB collection."""
        try:
            if not self.client:
                self._connect()
            
            # Check if collection exists and has documents
            collection_count = self.collection.count_documents({})
            print(f"[MongoDBOrigin] Collection {self.database_name}.{self.collection_name} has {collection_count} documents")
            
            if collection_count == 0:
                print(f"[MongoDBOrigin] Warning: Collection {self.database_name}.{self.collection_name} is empty")
                return []
            
            cursor = self.collection.find({}).skip(skip).limit(limit)
            documents = []
            
            for doc in cursor:
                try:
                    # Extract content - try common fields
                    content = None
                    if 'content' in doc:
                        content = str(doc['content'])
                    elif 'text' in doc:
                        content = str(doc['text'])
                    elif 'body' in doc:
                        content = str(doc['body'])
                    else:
                        # Use entire document as JSON string
                        import json
                        content = json.dumps(doc, default=str)
                    
                    # Get title/name
                    title = doc.get('title') or doc.get('name') or doc.get('_id')
                    
                    origin_doc = OriginDocument(
                        origin_id=str(doc.get('_id', '')),
                        title=str(title) if title else None,
                        content_preview=content[:200] if content else None,
                        metadata={k: v for k, v in doc.items() if k not in ['_id', 'content', 'text', 'body']},
                        size=len(content) if content else None,
                        created_at=doc.get('created_at') if isinstance(doc.get('created_at'), datetime) else None
                    )
                    documents.append(origin_doc)
                except Exception as doc_error:
                    print(f"[MongoDBOrigin] Error processing document {doc.get('_id', 'unknown')}: {doc_error}")
                    continue
            
            print(f"[MongoDBOrigin] Successfully loaded {len(documents)} documents")
            return documents
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"[MongoDBOrigin] Error listing documents: {error_trace}")
            raise
    
    def get_document(self, origin_id: str) -> Optional[Dict[str, Any]]:
        """Get full document from MongoDB."""
        try:
            if not self.client:
                self._connect()
            
            from bson import ObjectId
            try:
                doc_id = ObjectId(origin_id)
            except:
                doc_id = origin_id
            
            doc = self.collection.find_one({'_id': doc_id})
            if not doc:
                return None
            
            # Extract content
            content = None
            if 'content' in doc:
                content = str(doc['content'])
            elif 'text' in doc:
                content = str(doc['text'])
            elif 'body' in doc:
                content = str(doc['body'])
            else:
                import json
                content = json.dumps(doc, default=str)
            
            return {
                'origin_id': str(doc.get('_id', '')),
                'content': content,
                'metadata': {k: v for k, v in doc.items() if k not in ['_id', 'content', 'text', 'body']}
            }
        except Exception as e:
            print(f"[MongoDBOrigin] Error getting document: {e}")
            return None
    
    def close(self):
        """Close MongoDB connection."""
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                print(f"[MongoDBOrigin] Error closing: {e}")

