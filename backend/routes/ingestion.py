"""Ingestion pipeline route handlers."""

from flask import Blueprint, request, jsonify
from typing import List
from datetime import datetime

from backend.services.ingestion_pipeline import IngestionPipeline
from backend.services.raw_document_store import RawDocumentStore
from backend.services.origin_mongodb_source import OriginMongoDBSource
from backend.models.raw_document import RawDocument
from backend.config import Config

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
    Ingest document(s) from an origin source into raw_documents.
    Supports both single document and batch operations.
    
    Request body (single document):
        {
            "origin_source_type": "mongodb|qdrant|filesystem",
            "origin_id": "document_id_in_origin",
            "origin_source_id": "optional_source_identifier",
            "connection_config": {...},
            "skip_duplicates": true
        }
    
    Request body (batch):
        {
            "origin_source_type": "mongodb|qdrant|filesystem",
            "origin_ids": ["id1", "id2", ...],
            "origin_source_id": "optional_source_identifier",
            "connection_config": {...},
            "skip_duplicates": true
        }
    """
    try:
        data = request.get_json()
        
        origin_source_type = data.get('origin_source_type')
        origin_id = data.get('origin_id')  # Single document
        origin_ids = data.get('origin_ids')  # Batch operation
        origin_source_id = data.get('origin_source_id')
        connection_config = data.get('connection_config')
        
        if not origin_source_type:
            return jsonify({'error': 'origin_source_type is required'}), 400
        
        # Determine if this is a batch operation
        is_batch = origin_ids is not None and isinstance(origin_ids, list)
        
        if is_batch:
            if not origin_ids:
                return jsonify({'error': 'origin_ids must be a non-empty list'}), 400
        else:
            if not origin_id:
                return jsonify({'error': 'origin_id is required (or use origin_ids for batch)'}), 400
        
        if not connection_config:
            return jsonify({'error': 'connection_config is required'}), 400
        
        mongodb_uri = request.headers.get('X-MongoDB-URI')
        skip_duplicates = data.get('skip_duplicates', True)
        
        # Ingest document(s)
        pipeline = IngestionPipeline(mongodb_uri=mongodb_uri)
        try:
            if is_batch:
                # Batch operation
                result = pipeline.ingest_origin_documents_batch(
                    origin_source_type=origin_source_type,
                    origin_ids=origin_ids,
                    origin_source_id=origin_source_id,
                    connection_config=connection_config,
                    skip_duplicates=skip_duplicates
                )
                
                # Return structured batch results
                return jsonify({
                    'message': f'Batch ingestion complete: {result["successful"]} successful, {result["skipped"]} skipped, {result["failed"]} failed',
                    'total': result['total'],
                    'successful': result['successful'],
                    'skipped': result['skipped'],
                    'failed': result['failed'],
                    'details': result['details']
                }), 200
            else:
                # Single document operation
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
        # Transform E11000 errors to user-friendly messages
        error_msg = str(e)
        if 'E11000' in error_msg or 'duplicate key' in error_msg.lower():
            return jsonify({
                'error': 'Duplicate document detected. This document has already been ingested.',
                'details': 'The document was skipped to prevent duplicates.'
            }), 400
        return jsonify({'error': f'Error ingesting document: {error_msg}'}), 500


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


@ingestion_bp.route('/ingest/origin/mongodb', methods=['POST'])
def ingest_from_mongodb_origin():
    """
    Ingest documents from MongoDB origin collection to semantic collection.
    Uses the new origin → semantic pattern (no raw_documents intermediate).
    
    Request body:
        {
            "mode": "all" | "since",
            "since_timestamp": "2024-01-01T00:00:00Z" (optional, for "since" mode),
            "skip_duplicates": true,
            "database_name": "optional_db_name" (defaults to Config.ORIGIN_DB_NAME),
            "collection_name": "optional_collection_name" (defaults to Config.ORIGIN_COLLECTION_NAME),
            "limit": 100 (optional, max documents to fetch)
        }
    """
    try:
        data = request.get_json() or {}
        
        mode = data.get('mode', 'all')  # 'all' or 'since'
        since_timestamp_str = data.get('since_timestamp')
        skip_duplicates = data.get('skip_duplicates', True)
        database_name = data.get('database_name')
        collection_name = data.get('collection_name')
        limit = data.get('limit')
        
        if mode not in ['all', 'since']:
            return jsonify({'error': 'mode must be "all" or "since"'}), 400
        
        if mode == 'since' and not since_timestamp_str:
            return jsonify({'error': 'since_timestamp is required when mode is "since"'}), 400
        
        mongodb_uri = request.headers.get('X-MongoDB-URI')
        
        if not mongodb_uri:
            return jsonify({'error': 'X-MongoDB-URI header is required'}), 400
        
        # Parse since_timestamp if provided
        since_timestamp = None
        if since_timestamp_str:
            try:
                from dateutil import parser
                since_timestamp = parser.parse(since_timestamp_str)
            except Exception as e:
                return jsonify({'error': f'Invalid since_timestamp format: {str(e)}'}), 400
        
        # Validate database_name and collection_name are provided
        if not database_name or not collection_name:
            return jsonify({
                'error': 'database_name and collection_name are required',
                'details': f'Received: database_name={database_name}, collection_name={collection_name}'
            }), 400
        
        # Create origin source
        try:
            origin_source = OriginMongoDBSource(
                mongodb_uri=mongodb_uri,
                database_name=database_name,
                collection_name=collection_name
            )
        except ValueError as e:
            # Check if it's a semantic collection error
            if 'semantic collection' in str(e).lower():
                return jsonify({
                    'error': str(e),
                    'details': 'Origin source must use origin collections, not semantic collections.'
                }), 400
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"[Ingestion Route] Error creating origin source: {str(e)}")
            print(error_trace)
            return jsonify({
                'error': f'Failed to connect to origin: {str(e)}',
                'details': 'Please check that the database and collection exist and are accessible.'
            }), 500
        
        # Fetch documents based on mode
        try:
            if mode == 'all':
                origin_documents = origin_source.fetch_all_documents(limit=limit)
            else:  # mode == 'since'
                if not since_timestamp:
                    return jsonify({'error': 'since_timestamp is required for "since" mode'}), 400
                origin_documents = origin_source.fetch_new_documents(since_timestamp, limit=limit)
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"[Ingestion Route] Error fetching documents: {str(e)}")
            print(error_trace)
            origin_source.close()
            return jsonify({
                'error': f'Failed to fetch documents: {str(e)}',
                'details': 'Please check that the collection exists and contains documents.'
            }), 500
        
        if not origin_documents:
            origin_source.close()
            return jsonify({
                'message': 'No documents found to ingest',
                'total': 0,
                'successful': 0,
                'skipped': 0,
                'failed': 0
            }), 200
        
        # Ingest documents to semantic collection
        # Create a shared MongoClient for the pipeline to use the same connection
        from pymongo import MongoClient
        try:
            # Create a client for the pipeline (it will create its own stores)
            pipeline = IngestionPipeline(mongodb_uri=mongodb_uri)
            try:
                result = pipeline.ingest_origin_documents_batch_to_semantic(
                    origin_documents=origin_documents,
                    skip_duplicates=skip_duplicates
                )
                
                # Get semantic collection name for response
                semantic_collection = Config.get_semantic_collection_name(collection_name)
                
                return jsonify({
                    'message': f'Ingestion complete: {result["successful"]} successful, {result["skipped"]} skipped, {result["failed"]} failed',
                    'origin_collection': f'{database_name}.{collection_name}',
                    'semantic_collection': f'{database_name}.{semantic_collection}',
                    'total': result['total'],
                    'successful': result['successful'],
                    'skipped': result['skipped'],
                    'failed': result['failed'],
                    'total_chunks_created': result.get('total_chunks_created', 0),
                    'details': result['details']
                }), 200
            finally:
                pipeline.close()
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"[Ingestion Route] Error in ingestion pipeline: {str(e)}")
            print(error_trace)
            return jsonify({
                'error': f'Failed to ingest documents: {str(e)}',
                'details': 'Please check the backend logs for more details.'
            }), 500
        finally:
            origin_source.close()
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Transform E11000 errors to user-friendly messages
        error_msg = str(e)
        if 'E11000' in error_msg or 'duplicate key' in error_msg.lower():
            return jsonify({
                'error': 'Duplicate document detected. This document has already been ingested.',
                'details': 'The document was skipped to prevent duplicates.'
            }), 400
        return jsonify({'error': f'Error ingesting from MongoDB origin: {error_msg}'}), 500

