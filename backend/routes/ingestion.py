"""Ingestion pipeline route handlers."""

from flask import Blueprint, request, jsonify
from typing import List

from backend.services.ingestion_pipeline import IngestionPipeline
from backend.services.raw_document_store import RawDocumentStore
from backend.models.raw_document import RawDocument

ingestion_bp = Blueprint('ingestion', __name__)


@ingestion_bp.route('/ingest/raw', methods=['GET'])
def list_raw_documents():
    """
    List raw documents with optional filters.
    
    Query parameters:
        status: Filter by status (pending, processing, processed, failed)
        origin_source_type: Filter by origin source type
        origin_source_id: Filter by origin source ID
        limit: Maximum number of documents (default: 100)
        skip: Number of documents to skip (default: 0)
    """
    try:
        mongodb_uri = request.headers.get('X-MongoDB-URI')
        
        # Debug logging
        print(f"[list_raw_documents] Received X-MongoDB-URI header: {'Present' if mongodb_uri else 'Missing'}")
        if mongodb_uri:
            print(f"[list_raw_documents] MongoDB URI length: {len(mongodb_uri)} characters")
        
        # Check if MongoDB URI is provided (handle empty strings)
        if not mongodb_uri or mongodb_uri.strip() == '':
            from backend.config import Config
            mongodb_uri = Config.MONGODB_URI
            print(f"[list_raw_documents] Using Config.MONGODB_URI: {'Present' if mongodb_uri else 'Missing'}")
            if not mongodb_uri or mongodb_uri.strip() == '':
                return jsonify({
                    'error': 'MongoDB URI is required. Please provide X-MongoDB-URI header or configure MONGODB_URI in environment variables.',
                    'details': 'You can set the MongoDB URI in the connection settings or configure it in your .env file.'
                }), 400
        
        status = request.args.get('status')
        origin_source_type = request.args.get('origin_source_type')
        origin_source_id = request.args.get('origin_source_id')
        limit = int(request.args.get('limit', 100))
        skip = int(request.args.get('skip', 0))
        
        # Initialize RawDocumentStore with better error handling
        try:
            raw_store = RawDocumentStore(mongodb_uri=mongodb_uri)
        except Exception as init_error:
            import traceback
            error_msg = str(init_error)
            error_trace = traceback.format_exc()
            print(f"[list_raw_documents] Error initializing RawDocumentStore: {error_msg}")
            print(error_trace)
            from backend.config import Config
            if Config.FLASK_DEBUG:
                return jsonify({
                    'error': f'Failed to connect to MongoDB: {error_msg}',
                    'type': type(init_error).__name__,
                    'traceback': error_trace,
                    'details': 'Please check your MongoDB URI and ensure the server is accessible.'
                }), 500
            else:
                return jsonify({
                    'error': f'Failed to connect to MongoDB: {error_msg}',
                    'details': 'Please check your MongoDB URI and ensure the server is accessible.'
                }), 500
        
        try:
            documents = raw_store.list_raw_documents(
                status=status,
                origin_source_type=origin_source_type,
                origin_source_id=origin_source_id,
                limit=limit,
                skip=skip
            )
            
            # Convert documents to dict, handling any serialization errors
            raw_documents_list = []
            for doc in documents:
                try:
                    raw_documents_list.append(doc.to_dict())
                except Exception as doc_error:
                    print(f"[list_raw_documents] Error serializing document {doc.raw_document_id}: {doc_error}")
                    import traceback
                    traceback.print_exc()
                    # Skip this document but continue with others
                    continue
            
            return jsonify({
                'raw_documents': raw_documents_list,
                'count': len(raw_documents_list)
            }), 200
        finally:
            raw_store.close()
        
    except ValueError as e:
        # Handle validation errors (e.g., missing MongoDB URI)
        import traceback
        error_msg = str(e)
        print(f"[list_raw_documents] Validation error: {error_msg}")
        traceback.print_exc()
        return jsonify({
            'error': f'Validation error: {error_msg}',
            'details': 'Please ensure MongoDB URI is properly configured.'
        }), 400
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_trace = traceback.format_exc()
        print(f"[list_raw_documents] ERROR: {error_msg}")
        print(error_trace)
        
        # Return detailed error in debug mode
        from backend.config import Config
        if Config.FLASK_DEBUG:
            return jsonify({
                'error': f'Error listing raw documents: {error_msg}',
                'type': type(e).__name__,
                'traceback': error_trace
            }), 500
        else:
            return jsonify({
                'error': f'Error listing raw documents: {error_msg}',
                'type': type(e).__name__
            }), 500


@ingestion_bp.route('/ingest/raw/<raw_document_id>', methods=['GET'])
def get_raw_document(raw_document_id: str):
    """Get a specific raw document."""
    try:
        mongodb_uri = request.headers.get('X-MongoDB-URI')
        
        raw_store = RawDocumentStore(mongodb_uri=mongodb_uri)
        doc = raw_store.get_raw_document(raw_document_id)
        raw_store.close()
        
        if not doc:
            return jsonify({'error': 'Raw document not found'}), 404
        
        return jsonify(doc.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': f'Error getting raw document: {str(e)}'}), 500


@ingestion_bp.route('/ingest/process', methods=['POST'])
def process_raw_documents():
    """
    Process raw documents into vector_data collection.
    
    Request body:
        {
            "raw_document_ids": ["id1", "id2", ...],
            "target_collection": "optional_collection_name"
        }
    """
    try:
        data = request.get_json()
        raw_document_ids = data.get('raw_document_ids', [])
        target_collection = data.get('target_collection')  # Can be "collection" or "database.collection"
        mongodb_uri = request.headers.get('X-MongoDB-URI')
        
        if not raw_document_ids:
            return jsonify({'error': 'raw_document_ids is required'}), 400
        
        if not isinstance(raw_document_ids, list):
            return jsonify({'error': 'raw_document_ids must be a list'}), 400
        
        # Log target collection format
        if target_collection:
            print(f"[Ingestion Route] Target collection: {target_collection} (format: {'database.collection' if '.' in target_collection else 'collection'})")
        
        # Process documents
        pipeline = IngestionPipeline(mongodb_uri=mongodb_uri)
        try:
            if len(raw_document_ids) == 1:
                # Single document
                result = pipeline.process_raw_document(raw_document_ids[0], target_collection)
                return jsonify(result), 200
            else:
                # Multiple documents
                result = pipeline.process_multiple_raw_documents(raw_document_ids, target_collection)
                return jsonify(result), 200
        finally:
            pipeline.close()
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error processing documents: {str(e)}'}), 500


@ingestion_bp.route('/ingest/origin', methods=['POST'])
def ingest_from_origin():
    """
    Ingest a document from an origin source into raw_documents.
    
    Request body:
        {
            "origin_source_type": "mongodb|qdrant|filesystem",
            "origin_id": "document_id_in_origin",
            "origin_source_id": "optional_source_identifier",
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
        
        origin_source_type = data.get('origin_source_type')
        origin_id = data.get('origin_id')
        origin_source_id = data.get('origin_source_id')
        connection_config = data.get('connection_config')
        
        if not origin_source_type:
            return jsonify({'error': 'origin_source_type is required'}), 400
        if not origin_id:
            return jsonify({'error': 'origin_id is required'}), 400
        if not connection_config:
            return jsonify({'error': 'connection_config is required'}), 400
        
        mongodb_uri = request.headers.get('X-MongoDB-URI')
        
        # Get skip_duplicates parameter (default: True)
        skip_duplicates = data.get('skip_duplicates', True)
        
        # Ingest document
        pipeline = IngestionPipeline(mongodb_uri=mongodb_uri)
        try:
            result = pipeline.ingest_origin_document(
                origin_source_type=origin_source_type,
                origin_id=origin_id,
                origin_source_id=origin_source_id,
                connection_config=connection_config,
                skip_duplicates=skip_duplicates
            )
            
            if result.get('skipped'):
                return jsonify({
                    'message': 'Document already ingested, skipped',
                    'raw_document_id': result.get('raw_document_id'),
                    'status': 'skipped',
                    'reason': result.get('reason')
                }), 200
            else:
                return jsonify({
                    'message': 'Document ingested successfully',
                    'raw_document_id': result.get('raw_document_id'),
                    'status': 'pending'
                }), 200
        finally:
            pipeline.close()
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error ingesting document: {str(e)}'}), 500


@ingestion_bp.route('/ingest/status', methods=['GET'])
def get_ingestion_status():
    """
    Get ingestion status summary.
    
    Returns counts of raw documents by status.
    """
    try:
        mongodb_uri = request.headers.get('X-MongoDB-URI')
        
        raw_store = RawDocumentStore(mongodb_uri=mongodb_uri)
        status_counts = raw_store.count_by_status()
        raw_store.close()
        
        return jsonify({
            'status_counts': status_counts,
            'total': sum(status_counts.values())
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error getting status: {str(e)}'}), 500


@ingestion_bp.route('/ingest/raw/<raw_document_id>', methods=['DELETE'])
def delete_raw_document(raw_document_id: str):
    """Delete a raw document."""
    try:
        mongodb_uri = request.headers.get('X-MongoDB-URI')
        
        raw_store = RawDocumentStore(mongodb_uri=mongodb_uri)
        deleted = raw_store.delete_raw_document(raw_document_id)
        raw_store.close()
        
        if not deleted:
            return jsonify({'error': 'Raw document not found'}), 404
        
        return jsonify({
            'message': 'Raw document deleted successfully',
            'raw_document_id': raw_document_id
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Error deleting raw document: {str(e)}'}), 500

