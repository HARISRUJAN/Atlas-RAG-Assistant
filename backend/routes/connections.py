"""Connection management routes."""

from flask import Blueprint, request, jsonify
import uuid
from typing import List, Dict, Any

from backend.models.connection import Connection, ConnectionStorage, ConnectionEncryption
from backend.services.providers import (
    MongoDBProvider, RedisProvider, QdrantProvider, PineconeProvider
)

connections_bp = Blueprint('connections', __name__)


def get_provider_instance(provider: str, uri: str, api_key: str = None) -> Any:
    """
    Get provider instance based on provider type.
    
    Args:
        provider: Provider type (mongo, redis, qdrant, pinecone)
        uri: Connection URI
        api_key: Optional API key
        
    Returns:
        Provider instance
    """
    providers = {
        'mongo': MongoDBProvider,
        'redis': RedisProvider,
        'qdrant': QdrantProvider,
        'pinecone': PineconeProvider
    }
    
    if provider not in providers:
        raise ValueError(f"Unknown provider: {provider}")
    
    ProviderClass = providers[provider]
    return ProviderClass(uri=uri, api_key=api_key)


@connections_bp.route('/connections', methods=['POST'])
def create_connection():
    """
    Create a new connection.
    
    Request body:
        {
            "provider": "mongo|redis|qdrant|pinecone",
            "display_name": "Connection name",
            "uri": "connection string or URL",
            "api_key": "optional API key"
        }
    
    Returns:
        JSON response with connection_id
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['provider', 'uri']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        provider = data['provider']
        if provider not in Connection.PROVIDERS:
            return jsonify({'error': f'Invalid provider: {provider}'}), 400
        
        # Validate URI format
        uri = data['uri']
        api_key = data.get('api_key')
        
        # Test connection
        provider_instance = get_provider_instance(provider, uri, api_key)
        if not provider_instance.test_connection():
            return jsonify({'error': 'Connection test failed. Please check your URI and credentials.'}), 400
        
        # Create connection
        connection_id = str(uuid.uuid4())
        connection = Connection(
            connection_id=connection_id,
            provider=provider,
            display_name=data.get('display_name', f'{provider.upper()} Connection'),
            uri=uri,
            api_key=api_key,
            scopes=[],
            status='active'
        )
        
        # Save connection
        storage = ConnectionStorage()
        storage.save(connection)
        storage.close()
        
        return jsonify({
            'connection_id': connection_id,
            'message': 'Connection created successfully'
        }), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Error creating connection: {str(e)}'}), 500


@connections_bp.route('/connections', methods=['GET'])
def list_connections():
    """
    List all connections.
    
    Returns:
        JSON response with list of connections
    """
    try:
        storage = ConnectionStorage()
        connections = storage.list_all()
        storage.close()
        
        # Test each connection status
        for conn in connections:
            try:
                provider_instance = get_provider_instance(conn.provider, conn.uri, conn.api_key)
                conn.status = 'active' if provider_instance.test_connection() else 'error'
                provider_instance.close()
            except:
                conn.status = 'error'
        
        return jsonify({
            'connections': [conn.to_dict(include_credentials=False) for conn in connections]
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error listing connections: {str(e)}'}), 500


@connections_bp.route('/connections/<connection_id>', methods=['GET'])
def get_connection(connection_id: str):
    """
    Get connection details.
    
    Args:
        connection_id: Connection identifier
        
    Returns:
        JSON response with connection details
    """
    try:
        storage = ConnectionStorage()
        connection = storage.get(connection_id)
        storage.close()
        
        if not connection:
            return jsonify({'error': 'Connection not found'}), 404
        
        return jsonify(connection.to_dict(include_credentials=False)), 200
        
    except Exception as e:
        return jsonify({'error': f'Error getting connection: {str(e)}'}), 500


@connections_bp.route('/connections/<connection_id>/consent', methods=['POST'])
def update_connection_scopes(connection_id: str):
    """
    Update connection scopes (permissions).
    
    Request body:
        {
            "scopes": ["list.indexes", "read.metadata", "read.vectors"]
        }
    
    Args:
        connection_id: Connection identifier
        
    Returns:
        JSON response with updated connection
    """
    try:
        data = request.get_json()
        scopes = data.get('scopes', [])
        
        # Validate scopes
        invalid_scopes = [s for s in scopes if s not in Connection.SCOPES]
        if invalid_scopes:
            return jsonify({'error': f'Invalid scopes: {invalid_scopes}'}), 400
        
        # Get connection
        storage = ConnectionStorage()
        connection = storage.get(connection_id)
        
        if not connection:
            storage.close()
            return jsonify({'error': 'Connection not found'}), 404
        
        # Update scopes
        connection.scopes = scopes
        storage.save(connection)
        storage.close()
        
        return jsonify(connection.to_dict(include_credentials=False)), 200
        
    except Exception as e:
        return jsonify({'error': f'Error updating scopes: {str(e)}'}), 500


@connections_bp.route('/connections/<connection_id>/test', methods=['POST'])
def test_connection(connection_id: str):
    """
    Test connection.
    
    Args:
        connection_id: Connection identifier
        
    Returns:
        JSON response with test result
    """
    try:
        storage = ConnectionStorage()
        connection = storage.get(connection_id)
        storage.close()
        
        if not connection:
            return jsonify({'error': 'Connection not found'}), 404
        
        # Test connection
        provider_instance = get_provider_instance(connection.provider, connection.uri, connection.api_key)
        is_connected = provider_instance.test_connection()
        provider_instance.close()
        
        # Update status
        storage = ConnectionStorage()
        connection.status = 'active' if is_connected else 'error'
        storage.save(connection)
        storage.close()
        
        return jsonify({
            'connection_id': connection_id,
            'status': 'connected' if is_connected else 'failed',
            'message': 'Connection successful' if is_connected else 'Connection failed'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error testing connection: {str(e)}'}), 500


@connections_bp.route('/connections/<connection_id>', methods=['DELETE'])
def delete_connection(connection_id: str):
    """
    Delete connection.
    
    Args:
        connection_id: Connection identifier
        
    Returns:
        JSON response with deletion status
    """
    try:
        storage = ConnectionStorage()
        deleted = storage.delete(connection_id)
        storage.close()
        
        if not deleted:
            return jsonify({'error': 'Connection not found'}), 404
        
        return jsonify({
            'message': 'Connection deleted successfully',
            'connection_id': connection_id
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error deleting connection: {str(e)}'}), 500


@connections_bp.route('/connections/<connection_id>/collections', methods=['GET'])
def list_connection_collections(connection_id: str):
    """
    List collections/indexes for a connection.
    
    Args:
        connection_id: Connection identifier
        
    Returns:
        JSON response with list of collections
    """
    try:
        storage = ConnectionStorage()
        connection = storage.get(connection_id)
        storage.close()
        
        if not connection:
            return jsonify({'error': 'Connection not found'}), 404
        
        # Get provider instance
        provider_instance = get_provider_instance(connection.provider, connection.uri, connection.api_key)
        
        # List collections
        collections = provider_instance.list_collections()
        provider_instance.close()
        
        return jsonify({
            'connection_id': connection_id,
            'provider': connection.provider,
            'collections': collections
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error listing collections: {str(e)}'}), 500

