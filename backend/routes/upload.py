"""File upload route handler."""

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from backend.utils.file_validator import validate_file
from backend.services.document_processor import DocumentProcessor
from backend.services.embedding_service import EmbeddingService
from backend.services.vector_store import VectorStoreService

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
        # Process document
        processor = DocumentProcessor()
        metadata, chunks = processor.process_file(file)
        
        # Generate embeddings for chunks
        embedding_service = EmbeddingService()
        chunk_texts = [chunk.content for chunk in chunks]
        embeddings = embedding_service.generate_embeddings(chunk_texts)
        
        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
        
        # Store in vector database
        vector_store = VectorStoreService()
        stored_count = vector_store.store_chunks(chunks)
        
        return jsonify({
            'message': 'File uploaded and processed successfully',
            'document_id': metadata.document_id,
            'file_name': metadata.file_name,
            'total_chunks': metadata.total_chunks,
            'stored_chunks': stored_count
        }), 200
        
    except ValueError as e:
        # Validation errors - provide clear message to user
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        # Log the full error for debugging
        import traceback
        print(f"Error processing file: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

