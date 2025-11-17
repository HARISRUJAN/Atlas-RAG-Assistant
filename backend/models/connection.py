"""Connection model for vector store providers."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pymongo import MongoClient
from cryptography.fernet import Fernet
import base64
import os
import hashlib

from backend.config import Config


class Connection:
    """Model for vector store connection with encrypted credentials."""
    
    PROVIDERS = ['mongo', 'redis', 'qdrant', 'pinecone']
    SCOPES = ['list.indexes', 'read.metadata', 'read.vectors', 'write.vectors']
    
    def __init__(
        self,
        connection_id: str,
        provider: str,
        display_name: str,
        uri: str,
        api_key: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        status: str = 'active',
        created_at: Optional[datetime] = None
    ):
        """
        Initialize connection.
        
        Args:
            connection_id: Unique connection identifier
            provider: Provider type (mongo, redis, qdrant, pinecone)
            display_name: User-friendly name
            uri: Connection URI/URL
            api_key: Optional API key (for Qdrant/Pinecone)
            scopes: List of granted permissions
            status: Connection status (active, inactive, error)
            created_at: Creation timestamp
        """
        if provider not in self.PROVIDERS:
            raise ValueError(f"Invalid provider: {provider}. Must be one of {self.PROVIDERS}")
        
        self.connection_id = connection_id
        self.provider = provider
        self.display_name = display_name
        self.uri = uri
        self.api_key = api_key
        self.scopes = scopes or []
        self.status = status
        self.created_at = created_at or datetime.utcnow()
    
    def to_dict(self, include_credentials: bool = False) -> Dict[str, Any]:
        """
        Convert connection to dictionary.
        
        Args:
            include_credentials: Whether to include encrypted credentials
            
        Returns:
            Dictionary representation
        """
        data = {
            'connection_id': self.connection_id,
            'provider': self.provider,
            'display_name': self.display_name,
            'scopes': self.scopes,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }
        
        if include_credentials:
            data['uri'] = self.uri
            if self.api_key:
                data['api_key'] = self.api_key
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], decrypt: bool = False) -> 'Connection':
        """
        Create connection from dictionary.
        
        Args:
            data: Dictionary with connection data
            decrypt: Whether to decrypt credentials
            
        Returns:
            Connection instance
        """
        if decrypt and 'encrypted_uri' in data:
            data['uri'] = ConnectionEncryption.decrypt(data['encrypted_uri'])
        if decrypt and 'encrypted_api_key' in data and data['encrypted_api_key']:
            data['api_key'] = ConnectionEncryption.decrypt(data['encrypted_api_key'])
        
        return cls(
            connection_id=data['connection_id'],
            provider=data['provider'],
            display_name=data['display_name'],
            uri=data.get('uri', ''),
            api_key=data.get('api_key'),
            scopes=data.get('scopes', []),
            status=data.get('status', 'active'),
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else datetime.utcnow()
        )


class ConnectionEncryption:
    """Handles encryption/decryption of connection credentials."""
    
    _fernet: Optional[Fernet] = None
    
    @classmethod
    def _get_fernet(cls) -> Fernet:
        """Get or create Fernet instance for encryption."""
        if cls._fernet is None:
            # Generate key from environment or create one
            key = os.getenv('CONNECTION_ENCRYPTION_KEY')
            if not key:
                # Generate a key based on MongoDB URI (for consistency)
                # In production, this should be a proper secret key
                seed = Config.MONGODB_URI or 'default-seed'
                key_bytes = hashlib.sha256(seed.encode()).digest()
                key = base64.urlsafe_b64encode(key_bytes).decode()
            
            cls._fernet = Fernet(key.encode())
        
        return cls._fernet
    
    @classmethod
    def encrypt(cls, value: str) -> str:
        """Encrypt a string value."""
        if not value:
            return ''
        return cls._get_fernet().encrypt(value.encode()).decode()
    
    @classmethod
    def decrypt(cls, encrypted_value: str) -> str:
        """Decrypt an encrypted string value."""
        if not encrypted_value:
            return ''
        return cls._get_fernet().decrypt(encrypted_value.encode()).decode()


class ConnectionStorage:
    """Handles storage and retrieval of connections."""
    
    def __init__(self, mongodb_uri: Optional[str] = None):
        """
        Initialize connection storage.
        
        Args:
            mongodb_uri: MongoDB URI for storage (defaults to Config.MONGODB_URI)
        """
        self.mongodb_uri = mongodb_uri or Config.MONGODB_URI
        self.db_name = 'rag_database'
        self.collection_name = 'connections'
        
        # Create MongoDB client
        self.client = MongoClient(self.mongodb_uri)
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]
        
        # Create index on connection_id
        self.collection.create_index('connection_id', unique=True)
    
    def save(self, connection: Connection) -> bool:
        """
        Save connection to storage.
        
        Args:
            connection: Connection instance
            
        Returns:
            True if successful
        """
        data = connection.to_dict(include_credentials=True)
        
        # Encrypt credentials
        data['encrypted_uri'] = ConnectionEncryption.encrypt(data.pop('uri'))
        if 'api_key' in data and data['api_key']:
            data['encrypted_api_key'] = ConnectionEncryption.encrypt(data.pop('api_key'))
        else:
            data['encrypted_api_key'] = None
        
        # Remove credentials from main data
        data.pop('uri', None)
        data.pop('api_key', None)
        
        # Upsert connection
        self.collection.update_one(
            {'connection_id': connection.connection_id},
            {'$set': data},
            upsert=True
        )
        
        return True
    
    def get(self, connection_id: str) -> Optional[Connection]:
        """
        Get connection by ID.
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            Connection instance or None
        """
        data = self.collection.find_one({'connection_id': connection_id})
        if not data:
            return None
        
        return Connection.from_dict(data, decrypt=True)
    
    def list_all(self) -> List[Connection]:
        """
        List all connections.
        
        Returns:
            List of Connection instances
        """
        connections = []
        for data in self.collection.find():
            # Don't decrypt for list view (performance)
            conn = Connection.from_dict(data, decrypt=False)
            connections.append(conn)
        
        return connections
    
    def delete(self, connection_id: str) -> bool:
        """
        Delete connection.
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            True if deleted
        """
        result = self.collection.delete_one({'connection_id': connection_id})
        return result.deleted_count > 0
    
    def close(self):
        """Close MongoDB connection."""
        self.client.close()

