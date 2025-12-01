"""Query route handler."""

from flask import Blueprint, request, jsonify

from backend.config import Config
from backend.models.query import QueryRequest
from backend.services.rag_service import RAGService
from backend.services.collection_service import validate_collection_for_query

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
        # Check if pipeline mode is requested (default: True for new pipeline)
        use_pipeline = data.get('use_pipeline', True)
        
        # Support vector_collection parameter for pipeline mode (e.g., "srugenai_db.movies")
        vector_collection = data.get('vector_collection')  # Can be "database.collection" format
        
        collection_names = query_request.collection_names if query_request.collection_names else (
            [query_request.collection_name] if query_request.collection_name else None
        )
        
        # If vector_collection is specified but no collection_names, use it as fallback
        # Otherwise, use all selected collections (don't override with single vector_collection)
        if not collection_names and vector_collection and use_pipeline:
            collection_names = [vector_collection]
            print(f"[Query Route] Using vector_collection as fallback: {vector_collection}")
        elif collection_names and vector_collection:
            # If both are provided, prefer collection_names (user's selection)
            print(f"[Query Route] Using selected collections: {collection_names} (vector_collection {vector_collection} ignored)")
        
        # Transform collection names to semantic collections (RAG must use semantic collections)
        if collection_names:
            semantic_collection_names = []
            for coll_name in collection_names:
                # Check if it's already a semantic collection
                if Config.is_semantic_collection(coll_name):
                    semantic_collection_names.append(coll_name)
                else:
                    # Transform to semantic collection
                    # Handle "database.collection" format
                    if '.' in coll_name:
                        parts = coll_name.split('.', 1)
                        if len(parts) == 2:
                            db_name, coll = parts
                            semantic_coll = Config.get_semantic_collection_name(coll)
                            semantic_collection_names.append(f"{db_name}.{semantic_coll}")
                        else:
                            semantic_collection_names.append(Config.get_semantic_collection_name(coll_name))
                    else:
                        semantic_collection_names.append(Config.get_semantic_collection_name(coll_name))
            
            collection_names = semantic_collection_names
            print(f"[Query Route] Transformed to semantic collections: {collection_names}")
        
        # Validate collections before querying
        if collection_names:
            for coll_name in collection_names:
                is_valid, error_msg = validate_collection_for_query(coll_name, mongodb_uri)
                if not is_valid:
                    print(f"[Query Route] Invalid collection '{coll_name}': {error_msg}")
                    return jsonify({'error': error_msg}), 400
        
        # Log collection selection for debugging
        print(f"[Query Route] Received query: '{query_request.query[:100]}...'")
        print(f"[Query Route] Collection names received: {collection_names}")
        print(f"[Query Route] Vector collection: {vector_collection}")
        print(f"[Query Route] Connection IDs: {connection_ids}")
        print(f"[Query Route] MongoDB URI provided: {mongodb_uri is not None}")
        
        # Use connection_ids if provided, otherwise fall back to MongoDB URI
        if connection_ids:
            rag_service = RAGService(
                connection_ids=connection_ids,
                collection_names=collection_names,
                use_pipeline=False  # Multi-provider mode doesn't use pipeline
            )
        else:
            # Use new pipeline mode by default (vector_data collection)
            # Or legacy mode if explicitly disabled
            rag_service = RAGService(
                collection_names=collection_names,
                mongodb_uri=mongodb_uri,
                use_pipeline=use_pipeline
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

