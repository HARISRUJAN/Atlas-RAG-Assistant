"""Ingestion pipeline service for two-stage RAG data processing."""

from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

from backend.models.raw_document import RawDocument
from backend.models.document import DocumentChunk
from backend.services.raw_document_store import RawDocumentStore
from backend.services.vector_data_store import VectorDataStore
from backend.services.origin_sources import create_origin_source
from backend.services.document_processor import DocumentProcessor
from backend.services.embedding_service import EmbeddingService
from backend.utils.chunking import chunk_text_with_line_numbers
from backend.config import Config


class IngestionPipeline:
    """Orchestrates the ingestion pipeline: origin → raw_documents → vector_data."""
    
    def __init__(
        self,
        raw_store: Optional[RawDocumentStore] = None,
        vector_store: Optional[VectorDataStore] = None,
        mongodb_uri: Optional[str] = None
    ):
        """
        Initialize ingestion pipeline.
        
        Args:
            raw_store: Optional RawDocumentStore instance
            vector_store: Optional VectorDataStore instance
            mongodb_uri: Optional MongoDB URI (used if stores not provided)
        """
        self.raw_store = raw_store or RawDocumentStore(mongodb_uri=mongodb_uri)
        self.vector_store = vector_store or VectorDataStore(mongodb_uri=mongodb_uri)
        self.embedding_service = EmbeddingService()
        self.document_processor = DocumentProcessor()
    
    def ingest_origin_document(
        self,
        origin_source_type: str,
        origin_id: str,
        origin_source_id: Optional[str] = None,
        connection_config: Optional[Dict[str, Any]] = None,
        skip_duplicates: bool = True
    ) -> Dict[str, Any]:
        """
        Ingest a document from an origin source into raw_documents.
        
        Args:
            origin_source_type: Type of origin source ('mongodb', 'qdrant', 'filesystem', 'file_upload')
            origin_id: Document ID in the origin source
            origin_source_id: Optional source identifier/connection ID
            connection_config: Connection configuration for origin source (if needed)
            skip_duplicates: If True, skip ingestion if document already exists
            
        Returns:
            Dictionary with 'raw_document_id' and 'skipped' status
        """
        try:
            print(f"[IngestionPipeline] Ingesting document from {origin_source_type}, origin_id: {origin_id}")
            
            # Check for duplicates if skip_duplicates is enabled
            if skip_duplicates:
                if self.raw_store.is_origin_ingested(origin_id, origin_source_type):
                    print(f"[IngestionPipeline] Document with origin_id '{origin_id}' already ingested, skipping")
                    # Get existing document ID
                    existing_doc = self.raw_store.get_raw_document_by_origin_id(origin_id)
                    return {
                        'raw_document_id': existing_doc.raw_document_id if existing_doc else None,
                        'skipped': True,
                        'reason': 'duplicate_origin_id'
                    }
            
            # For file_upload, the content is already processed
            if origin_source_type == 'file_upload':
                # This case is handled separately in upload route
                raise ValueError("file_upload should use store_raw_document directly")
            
            # Create origin source and fetch document
            if not connection_config:
                raise ValueError(f"connection_config required for origin_source_type: {origin_source_type}")
            
            origin_source = create_origin_source(
                source_type=origin_source_type,
                source_id=origin_source_id or 'temp',
                connection_config=connection_config
            )
            
            # Get document from origin
            doc_data = origin_source.get_document(origin_id)
            if not doc_data:
                raise ValueError(f"Document not found in origin: {origin_id}")
            
            # Create raw document
            raw_doc = RawDocument(
                raw_document_id=str(uuid.uuid4()),
                origin_id=origin_id,
                origin_source_type=origin_source_type,
                origin_source_id=origin_source_id,
                raw_content=doc_data.get('content', ''),
                content_type='text',
                metadata=doc_data.get('metadata', {})
            )
            
            # Store in raw_documents (will fail if unique constraint violated)
            try:
                raw_document_id = self.store_raw_document(raw_doc)
                origin_source.close()
                
                print(f"[IngestionPipeline] Successfully ingested document, raw_document_id: {raw_document_id}")
                return {
                    'raw_document_id': raw_document_id,
                    'skipped': False,
                    'reason': None
                }
            except Exception as store_error:
                # Check if it's a duplicate key error
                if 'duplicate key' in str(store_error).lower() or 'E11000' in str(store_error):
                    print(f"[IngestionPipeline] Duplicate detected during insert: {origin_id}")
                    existing_doc = self.raw_store.get_raw_document_by_origin_id(origin_id)
                    origin_source.close()
                    return {
                        'raw_document_id': existing_doc.raw_document_id if existing_doc else None,
                        'skipped': True,
                        'reason': 'duplicate_origin_id'
                    }
                else:
                    origin_source.close()
                    raise
            
        except Exception as e:
            print(f"[IngestionPipeline] Error ingesting origin document: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def is_origin_ingested(self, origin_id: str, origin_source_type: Optional[str] = None) -> bool:
        """
        Check if an origin document has already been ingested.
        
        Args:
            origin_id: Origin document ID
            origin_source_type: Optional origin source type
            
        Returns:
            True if document is already ingested
        """
        return self.raw_store.is_origin_ingested(origin_id, origin_source_type)
    
    def store_raw_document(self, raw_doc: RawDocument) -> str:
        """
        Store a raw document in raw_documents collection.
        
        Args:
            raw_doc: RawDocument instance
            
        Returns:
            raw_document_id
        """
        try:
            return self.raw_store.store_raw_document(raw_doc)
        except Exception as e:
            print(f"[IngestionPipeline] Error storing raw document: {e}")
            raise
    
    def chunk_document(self, raw_doc: RawDocument) -> List[DocumentChunk]:
        """
        Chunk a raw document into text chunks with semantic chunking.
        
        Args:
            raw_doc: RawDocument instance
            
        Returns:
            List of DocumentChunk instances (without embeddings)
        """
        try:
            print(f"[IngestionPipeline] Chunking document: {raw_doc.raw_document_id}")
            
            # Handle JSON content - try to parse and format for better chunking
            content = raw_doc.raw_content
            if raw_doc.content_type == 'text' and content.strip().startswith('{'):
                try:
                    import json
                    # Try to parse JSON and format it nicely for chunking
                    parsed = json.loads(content)
                    # Format JSON with indentation for better semantic chunking
                    content = json.dumps(parsed, indent=2, ensure_ascii=False)
                    print(f"[IngestionPipeline] Parsed and formatted JSON content for better chunking")
                except (json.JSONDecodeError, ValueError):
                    # Not valid JSON, use as-is
                    pass
            
            # Chunk the raw content using semantic chunking
            chunks_data = chunk_text_with_line_numbers(content)
            
            if not chunks_data:
                raise ValueError(f"No chunks created from raw document {raw_doc.raw_document_id}")
            
            print(f"[IngestionPipeline] Created {len(chunks_data)} semantic chunks")
            
            # Create DocumentChunk instances
            chunks = []
            file_name = raw_doc.metadata.get('file_name') or raw_doc.metadata.get('title') or f"origin_{raw_doc.origin_id}"
            document_id = str(uuid.uuid4())  # New document ID for this processing
            
            for idx, (chunk_text, line_start, line_end) in enumerate(chunks_data):
                chunk = DocumentChunk(
                    chunk_id=f"{raw_doc.raw_document_id}_chunk_{idx}",
                    document_id=document_id,
                    file_name=file_name,
                    chunk_index=idx,
                    content=chunk_text,
                    line_start=line_start,
                    line_end=line_end,
                    metadata={
                        **raw_doc.metadata,
                        'raw_document_id': raw_doc.raw_document_id,
                        'origin_source_type': raw_doc.origin_source_type
                    },
                    origin_id=raw_doc.origin_id,
                    raw_document_id=raw_doc.raw_document_id
                )
                chunks.append(chunk)
            
            print(f"[IngestionPipeline] Created {len(chunks)} chunks from raw document")
            return chunks
            
        except Exception as e:
            print(f"[IngestionPipeline] Error chunking document: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def embed_chunks(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """
        Generate embeddings for chunks.
        
        Args:
            chunks: List of DocumentChunk instances (without embeddings)
            
        Returns:
            List of DocumentChunk instances with embeddings
        """
        try:
            print(f"[IngestionPipeline] Generating embeddings for {len(chunks)} chunks")
            
            # Generate embeddings in batch
            chunk_texts = [chunk.content for chunk in chunks]
            embeddings = self.embedding_service.generate_embeddings(chunk_texts)
            
            # Add embeddings to chunks
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding
            
            print(f"[IngestionPipeline] Generated embeddings for {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            print(f"[IngestionPipeline] Error generating embeddings: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def store_vector_chunks(self, chunks: List[DocumentChunk]) -> int:
        """
        Store chunks with embeddings in vector_data collection.
        
        Args:
            chunks: List of DocumentChunk instances with embeddings
            
        Returns:
            Number of chunks stored
        """
        try:
            if not chunks:
                print("[IngestionPipeline] No chunks to store")
                return 0
            
            # Validate all chunks have embeddings
            chunks_without_embeddings = [c for c in chunks if not c.embedding]
            if chunks_without_embeddings:
                raise ValueError(f"{len(chunks_without_embeddings)} chunks missing embeddings")
            
            count = self.vector_store.store_chunks(chunks)
            print(f"[IngestionPipeline] Stored {count} chunks in vector_data collection")
            return count
            
        except Exception as e:
            print(f"[IngestionPipeline] Error storing vector chunks: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def process_raw_document(
        self,
        raw_document_id: str,
        target_collection: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a raw document through the full pipeline: chunk → embed → store.
        
        Args:
            raw_document_id: Raw document ID
            target_collection: Optional target collection name for vector_data
            
        Returns:
            Dictionary with processing results
        """
        try:
            print(f"[IngestionPipeline] Processing raw document: {raw_document_id}")
            
            # Get raw document
            raw_doc = self.raw_store.get_raw_document(raw_document_id)
            if not raw_doc:
                raise ValueError(f"Raw document not found: {raw_document_id}")
            
            # Update status to processing
            self.raw_store.update_status(raw_document_id, 'processing')
            
            # Step 1: Chunk document (semantic chunking)
            print(f"[IngestionPipeline] Step 1/3: Chunking document {raw_document_id}...")
            chunks = self.chunk_document(raw_doc)
            print(f"[IngestionPipeline] ✓ Created {len(chunks)} semantic chunks")
            
            # Step 2: Generate embeddings
            print(f"[IngestionPipeline] Step 2/3: Generating vector embeddings for {len(chunks)} chunks...")
            chunks = self.embed_chunks(chunks)
            print(f"[IngestionPipeline] ✓ Generated {len(chunks)} embeddings")
            
            # Step 3: Store in vector_data (use target_collection if provided)
            print(f"[IngestionPipeline] Step 3/3: Storing chunks in vector collection...")
            if target_collection:
                # Create new vector store with target collection
                # target_collection can be "collection" or "database.collection" format
                vector_store = VectorDataStore(
                    collection_name=target_collection,
                    mongodb_uri=self.raw_store.mongodb_uri
                )
                stored_count = vector_store.store_chunks(chunks)
                vector_store.close()
                print(f"[IngestionPipeline] ✓ Stored {stored_count} chunks in {target_collection}")
            else:
                stored_count = self.store_vector_chunks(chunks)
                print(f"[IngestionPipeline] ✓ Stored {stored_count} chunks in default vector collection")
            
            # Update status to processed
            self.raw_store.update_status(raw_document_id, 'processed')
            print(f"[IngestionPipeline] ✓ Document {raw_document_id} fully processed")
            
            result = {
                'raw_document_id': raw_document_id,
                'chunks_created': len(chunks),
                'chunks_stored': stored_count,
                'status': 'success'
            }
            
            print(f"[IngestionPipeline] Successfully processed raw document: {raw_document_id}")
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"[IngestionPipeline] Error processing raw document: {error_msg}")
            
            # Update status to failed
            try:
                self.raw_store.update_status(raw_document_id, 'failed', error_message=error_msg)
            except:
                pass
            
            raise
    
    def process_multiple_raw_documents(
        self,
        raw_document_ids: List[str],
        target_collection: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process multiple raw documents.
        
        Args:
            raw_document_ids: List of raw document IDs
            target_collection: Optional target collection name
            
        Returns:
            Dictionary with processing results
        """
        results = {
            'total': len(raw_document_ids),
            'successful': 0,
            'failed': 0,
            'total_chunks_stored': 0,
            'chunks_stored': 0,  # Alias for compatibility
            'details': []
        }
        
        print(f"[IngestionPipeline] Processing {len(raw_document_ids)} raw document(s)...")
        
        for idx, raw_document_id in enumerate(raw_document_ids, 1):
            try:
                print(f"[IngestionPipeline] Processing document {idx}/{len(raw_document_ids)}: {raw_document_id}")
                result = self.process_raw_document(raw_document_id, target_collection)
                results['successful'] += 1
                chunks_stored = result.get('chunks_stored', 0)
                results['total_chunks_stored'] += chunks_stored
                results['chunks_stored'] = results['total_chunks_stored']  # Update alias
                results['details'].append({
                    'raw_document_id': raw_document_id,
                    'status': 'success',
                    **result
                })
                print(f"[IngestionPipeline] ✓ Document {idx}/{len(raw_document_ids)} processed: {chunks_stored} chunks stored")
            except Exception as e:
                results['failed'] += 1
                error_msg = str(e)
                print(f"[IngestionPipeline] ✗ Document {idx}/{len(raw_document_ids)} failed: {error_msg}")
                results['details'].append({
                    'raw_document_id': raw_document_id,
                    'status': 'failed',
                    'error': error_msg
                })
        
        print(f"[IngestionPipeline] Batch processing complete: {results['successful']} successful, {results['failed']} failed, {results['total_chunks_stored']} total chunks stored")
        return results
    
    def close(self):
        """Close all connections."""
        if self.raw_store:
            self.raw_store.close()
        if self.vector_store:
            self.vector_store.close()

