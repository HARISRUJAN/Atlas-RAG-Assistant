"""Origin source management route handlers."""

from flask import Blueprint, request, jsonify

from backend.services.origin_sources import create_origin_source

origin_bp = Blueprint('origin', __name__)


@origin_bp.route('/origin/sources', methods=['GET'])
def list_source_types():
    """
    List available origin source types.
    
    Returns:
        List of supported origin source types
    """
    return jsonify({
        'source_types': [
            {
                'type': 'mongodb',
                'name': 'MongoDB Collection',
                'description': 'Read documents from a MongoDB collection',
                'required_config': ['uri', 'database_name', 'collection_name']
            },
            {
                'type': 'qdrant',
                'name': 'Qdrant Collection',
                'description': 'Read documents from a Qdrant collection',
                'required_config': ['uri', 'collection_name']
            },
            {
                'type': 'filesystem',
                'name': 'File System',
                'description': 'Read files from a directory',
                'required_config': ['base_path']
            },
            {
                'type': 'file_upload',
                'name': 'File Upload',
                'description': 'Upload files directly',
                'required_config': []
            }
        ]
    }), 200


@origin_bp.route('/origin/connect', methods=['POST'])
def connect_origin():
    """
    Test connection to an origin source.
    
    Request body:
        {
            "source_type": "mongodb|qdrant|filesystem",
            "connection_config": {
                "uri": "...",
                "api_key": "...",
                "database_name": "...",
                "collection_name": "...",
                "base_path": "..." (for filesystem)
            }
        }
    """
    try:
        data = request.get_json()
        source_type = data.get('source_type')
        connection_config = data.get('connection_config')
        
        if not source_type:
            return jsonify({'error': 'source_type is required'}), 400
        if not connection_config:
            return jsonify({'error': 'connection_config is required'}), 400
        
        # Create origin source and test connection
        origin_source = create_origin_source(
            source_type=source_type,
            source_id='test',
            connection_config=connection_config
        )
        
        try:
            is_connected = origin_source.test_connection()
            
            if is_connected:
                return jsonify({
                    'status': 'connected',
                    'message': f'Successfully connected to {source_type} source'
                }), 200
            else:
                return jsonify({
                    'status': 'failed',
                    'message': f'Failed to connect to {source_type} source'
                }), 400
        finally:
            origin_source.close()
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'error': f'Error connecting to origin: {str(e)}'
        }), 500


@origin_bp.route('/origin/<source_type>/documents', methods=['POST'])
def list_origin_documents(source_type: str):
    """
    List documents from an origin source.
    
    Request body:
        {
            "connection_config": {
                "uri": "...",
                "api_key": "...",
                "database_name": "...",
                "collection_name": "...",
                "base_path": "..." (for filesystem)
            },
            "limit": 100,
            "skip": 0
        }
    """
    try:
        data = request.get_json()
        connection_config = data.get('connection_config')
        limit = data.get('limit', 100)
        skip = data.get('skip', 0)
        
        if not connection_config:
            return jsonify({'error': 'connection_config is required'}), 400
        
        # Create origin source
        origin_source = create_origin_source(
            source_type=source_type,
            source_id='browse',
            connection_config=connection_config
        )
        
        try:
            documents = origin_source.list_documents(limit=limit, skip=skip)
            
            return jsonify({
                'documents': [doc.to_dict() for doc in documents],
                'count': len(documents),
                'source_type': source_type
            }), 200
        finally:
            origin_source.close()
        
    except ValueError as e:
        # Handle validation errors (missing required fields)
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': f'Validation error: {str(e)}',
            'details': 'Please check that connection_config contains all required fields (uri, database_name, collection_name for MongoDB)'
        }), 400
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[list_origin_documents] Error: {error_trace}")
        return jsonify({
            'error': f'Error listing documents: {str(e)}',
            'type': type(e).__name__
        }), 500


@origin_bp.route('/origin/<source_type>/documents/<origin_id>', methods=['POST'])
def get_origin_document(source_type: str, origin_id: str):
    """
    Get a specific document from an origin source.
    
    Request body:
        {
            "connection_config": {
                "uri": "...",
                "api_key": "...",
                "database_name": "...",
                "collection_name": "...",
                "base_path": "..." (for filesystem)
            }
        }
    """
    try:
        data = request.get_json()
        connection_config = data.get('connection_config')
        
        if not connection_config:
            return jsonify({'error': 'connection_config is required'}), 400
        
        # Create origin source
        origin_source = create_origin_source(
            source_type=source_type,
            source_id='get',
            connection_config=connection_config
        )
        
        try:
            doc_data = origin_source.get_document(origin_id)
            
            if not doc_data:
                return jsonify({'error': 'Document not found'}), 404
            
            return jsonify({
                'document': doc_data,
                'source_type': source_type
            }), 200
        finally:
            origin_source.close()
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error getting document: {str(e)}'}), 500

