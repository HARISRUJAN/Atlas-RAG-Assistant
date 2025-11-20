"""File upload route handler."""

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime

from backend.utils.file_validator import validate_file
from backend.services.document_processor import DocumentProcessor
from backend.services.embedding_service import EmbeddingService
from backend.services.vector_store import VectorStoreService
from backend.services.raw_document_store import RawDocumentStore
from backend.models.raw_document import RawDocument

upload_bp = Blueprint('upload', __name__)


@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    Handle file upload and processing.
    
    Returns:
        JSON response with upload status and document info
    """
    # Check if file is present
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    # Validate file
    is_valid, error_message = validate_file(file)
    if not is_valid:
        return jsonify({'error': error_message}), 400
    
    try:
        # Get connection ID or MongoDB URI (for backward compatibility)
        connection_id = request.form.get('connection_id') or request.headers.get('X-Connection-ID')
        mongodb_uri = request.headers.get('X-MongoDB-URI')
        
        # Check if immediate processing is requested (backward compatibility)
        immediate_process = request.form.get('immediate_process', 'false').lower() == 'true'
        
        # Process document to extract text
        processor = DocumentProcessor()
        metadata, chunks = processor.process_file(file)
        
        # Create raw document
        raw_doc = RawDocument(
            raw_document_id=str(uuid.uuid4()),
            origin_id=metadata.document_id,
            origin_source_type='file_upload',
            origin_source_id=connection_id,
            raw_content='\n'.join([chunk.content for chunk in chunks]),  # Combine all chunks
            content_type='text',
            metadata={
                'file_name': metadata.file_name,
                'file_type': metadata.file_type,
                'file_size': metadata.file_size,
                'upload_date': metadata.upload_date.isoformat(),
                'total_chunks': metadata.total_chunks
            },
            status='pending'
        )
        
        # Store in raw_documents collection
        raw_store = RawDocumentStore(mongodb_uri=mongodb_uri)
        raw_document_id = raw_store.store_raw_document(raw_doc)
        
        response_data = {
            'message': 'File uploaded successfully',
            'raw_document_id': raw_document_id,
            'document_id': metadata.document_id,
            'file_name': metadata.file_name,
            'total_chunks': metadata.total_chunks,
            'status': 'pending',
            'note': 'Document stored in raw_documents. Use /api/ingest/process to convert to vectors.'
        }
        
        # If immediate processing requested (backward compatibility)
        if immediate_process:
            from backend.services.ingestion_pipeline import IngestionPipeline
            pipeline = IngestionPipeline(mongodb_uri=mongodb_uri)
            try:
                result = pipeline.process_raw_document(raw_document_id)
                response_data['message'] = 'File uploaded and processed successfully'
                response_data['status'] = 'processed'
                response_data['chunks_stored'] = result['chunks_stored']
                pipeline.close()
            except Exception as e:
                response_data['processing_error'] = str(e)
            finally:
                pipeline.close()
        
        raw_store.close()
        
        return jsonify(response_data), 200
        
    except ValueError as e:
        # Validation errors - provide clear message to user
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        # Log the full error for debugging
        import traceback
        print(f"Error processing file: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

