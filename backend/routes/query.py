"""Query route handler."""

from flask import Blueprint, request, jsonify

from backend.config import Config
from backend.models.query import QueryRequest
from backend.services.rag_service import RAGService

query_bp = Blueprint('query', __name__)


@query_bp.route('/query', methods=['POST'])
def query_documents():
    """
    Handle query requests.
    
    Returns:
        JSON response with answer and sources
    """
    # Parse request
    data = request.get_json()
    
    if not data or 'query' not in data:
        return jsonify({'error': 'Query text is required'}), 400
    
    try:
        # Get connection IDs or MongoDB URI (for backward compatibility)
        connection_ids = data.get('connection_ids')
        mongodb_uri = request.headers.get('X-MongoDB-URI')
        
        # Create query request
        query_request = QueryRequest.from_dict(data)
        
        # Process query through RAG pipeline
        collection_names = query_request.collection_names if query_request.collection_names else (
            [query_request.collection_name] if query_request.collection_name else None
        )
        
        # Log collection selection for debugging
        print(f"[Query Route] Received query: '{query_request.query[:100]}...'")
        print(f"[Query Route] Collection names received: {collection_names}")
        print(f"[Query Route] Connection IDs: {connection_ids}")
        print(f"[Query Route] MongoDB URI provided: {mongodb_uri is not None}")
        
        # Use connection_ids if provided, otherwise fall back to MongoDB URI
        if connection_ids:
            rag_service = RAGService(
                connection_ids=connection_ids,
                collection_names=collection_names
            )
        else:
            # Backward compatibility: use MongoDB URI
            rag_service = RAGService(
                collection_names=collection_names,
                mongodb_uri=mongodb_uri
            )
        
        response = rag_service.query(query_request)
        
        # Cleanup
        if hasattr(rag_service, 'unified_store') and rag_service.unified_store:
            rag_service.unified_store.close()
        elif hasattr(rag_service, 'vector_stores'):
            for vs in rag_service.vector_stores:
                vs.close()
        elif hasattr(rag_service, 'vector_store') and rag_service.vector_store:
            rag_service.vector_store.close()
        
        return jsonify(response.to_dict()), 200
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"[Query Route] ERROR processing query: {error_msg}")
        traceback.print_exc()
        
        # Return detailed error in debug mode
        if Config.FLASK_DEBUG:
            return jsonify({
                'error': f'Error processing query: {error_msg}',
                'traceback': traceback.format_exc()
            }), 500
        else:
            return jsonify({'error': f'Error processing query: {error_msg}'}), 500

