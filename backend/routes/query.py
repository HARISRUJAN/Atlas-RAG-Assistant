"""Query route handler."""

from flask import Blueprint, request, jsonify

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
        # Create query request
        query_request = QueryRequest.from_dict(data)
        
        # Process query through RAG pipeline
        rag_service = RAGService()
        response = rag_service.query(query_request)
        
        return jsonify(response.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': f'Error processing query: {str(e)}'}), 500

