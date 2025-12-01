"""Ingestion pipeline service for two-stage RAG data processing."""

from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

from backend.models.raw_document import RawDocument
from backend.models.document import DocumentChunk
from backend.services.raw_document_store import RawDocumentStore
from backend.services.vector_data_store import VectorDataStore
from backend.services.origin_sources import create_origin_source
from backend.services.origin_mongodb_source import OriginMongoDBSource
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
            
            # Store in raw_documents using upsert pattern (atomic duplicate handling)
            # This is idempotent and safe to retry
            try:
                upsert_result = self.raw_store.store_raw_document_upsert(raw_doc)
                origin_source.close()
                
                raw_document_id = upsert_result['raw_document_id']
                was_duplicate = upsert_result['was_duplicate']
                
                if was_duplicate:
                    print(f"[IngestionPipeline] Document with origin_id '{origin_id}' already existed, skipped duplicate")
                    return {
                        'raw_document_id': raw_document_id,
                        'skipped': True,
                        'reason': 'duplicate_origin_id',
                        'was_duplicate': True
                    }
                else:
                    print(f"[IngestionPipeline] Successfully ingested new document, raw_document_id: {raw_document_id}")
                    return {
                        'raw_document_id': raw_document_id,
                        'skipped': False,
                        'reason': None,
                        'was_duplicate': False
                    }
            except Exception as store_error:
                # Fallback error handling (should rarely be needed with upsert)
                error_str = str(store_error).lower()
                if 'duplicate key' in error_str or 'E11000' in error_str:
                    print(f"[IngestionPipeline] Duplicate detected during upsert (fallback): {origin_id}")
                    existing_doc = self.raw_store.get_raw_document_by_origin_id(origin_id, origin_source_type)
                    origin_source.close()
                    return {
                        'raw_document_id': existing_doc.raw_document_id if existing_doc else None,
                        'skipped': True,
                        'reason': 'duplicate_origin_id',
                        'was_duplicate': True
                    }
                else:
                    origin_source.close()
                    raise
            
        except ValueError as e:
            # Re-raise ValueError as-is (already user-friendly)
            print(f"[IngestionPipeline] Validation error ingesting origin document: {e}")
            raise
        except Exception as e:
            error_msg = str(e)
            print(f"[IngestionPipeline] Error ingesting origin document: {error_msg}")
            import traceback
            traceback.print_exc()
            # Transform common errors to user-friendly messages
            if 'E11000' in error_msg or 'duplicate key' in error_msg.lower():
                raise ValueError(f"Document with origin_id '{origin_id}' already exists in the system")
            if 'not found' in error_msg.lower() or 'does not exist' in error_msg.lower():
                raise ValueError(f"Document '{origin_id}' not found in origin source")
            if 'connection' in error_msg.lower() or 'timeout' in error_msg.lower():
                raise ConnectionError(f"Failed to connect to origin source: {error_msg}")
            # For other errors, wrap in a user-friendly message
            raise ValueError(f"Failed to ingest document: {error_msg}")
    
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
    
    def ingest_origin_documents_batch(
        self,
        origin_source_type: str,
        origin_ids: List[str],
        origin_source_id: Optional[str] = None,
        connection_config: Optional[Dict[str, Any]] = None,
        skip_duplicates: bool = True
    ) -> Dict[str, Any]:
        """
        Ingest multiple documents from an origin source with partial success handling.
        Continues processing even if some documents fail.
        
        Args:
            origin_source_type: Type of origin source ('mongodb', 'qdrant', 'filesystem')
            origin_ids: List of document IDs in the origin source
            origin_source_id: Optional source identifier/connection ID
            connection_config: Connection configuration for origin source
            skip_duplicates: If True, skip ingestion if document already exists
            
        Returns:
            Dictionary with:
                - total: Total number of documents attempted
                - successful: Number successfully ingested
                - skipped: Number skipped (duplicates)
                - failed: Number that failed
                - details: List of results for each document
        """
        results = {
            'total': len(origin_ids),
            'successful': 0,
            'skipped': 0,
            'failed': 0,
            'details': []
        }
        
        if not origin_ids:
            return results
        
        print(f"[IngestionPipeline] Starting batch ingestion of {len(origin_ids)} documents from {origin_source_type}")
        
        # Create origin source once for all documents (more efficient)
        origin_source = None
        try:
            if connection_config:
                origin_source = create_origin_source(
                    source_type=origin_source_type,
                    source_id=origin_source_id or 'temp',
                    connection_config=connection_config
                )
        except Exception as e:
            print(f"[IngestionPipeline] Error creating origin source: {e}")
            # If we can't create the source, all documents fail
            for origin_id in origin_ids:
                results['failed'] += 1
                results['details'].append({
                    'origin_id': origin_id,
                    'status': 'failed',
                    'error': f"Failed to create origin source: {str(e)}"
                })
            return results
        
        # Process each document individually
        for idx, origin_id in enumerate(origin_ids, 1):
            try:
                print(f"[IngestionPipeline] Processing document {idx}/{len(origin_ids)}: {origin_id}")
                
                # Use the single document ingestion method
                result = self.ingest_origin_document(
                    origin_source_type=origin_source_type,
                    origin_id=origin_id,
                    origin_source_id=origin_source_id,
                    connection_config=connection_config,
                    skip_duplicates=skip_duplicates
                )
                
                if result.get('skipped'):
                    results['skipped'] += 1
                    results['details'].append({
                        'origin_id': origin_id,
                        'status': 'skipped',
                        'raw_document_id': result.get('raw_document_id'),
                        'reason': result.get('reason', 'duplicate_origin_id')
                    })
                else:
                    results['successful'] += 1
                    results['details'].append({
                        'origin_id': origin_id,
                        'status': 'success',
                        'raw_document_id': result.get('raw_document_id')
                    })
                    
            except Exception as e:
                results['failed'] += 1
                error_msg = str(e)
                print(f"[IngestionPipeline] Error ingesting document {origin_id}: {error_msg}")
                results['details'].append({
                    'origin_id': origin_id,
                    'status': 'failed',
                    'error': error_msg
                })
                # Continue processing other documents
                continue
        
        # Close origin source
        if origin_source:
            try:
                origin_source.close()
            except:
                pass
        
        print(f"[IngestionPipeline] Batch ingestion complete: {results['successful']} successful, {results['skipped']} skipped, {results['failed']} failed")
        return results
    
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
    
    def ingest_origin_document_to_semantic(
        self,
        origin_document: Dict[str, Any],
        skip_duplicates: bool = True
    ) -> Dict[str, Any]:
        """
        Ingest a normalized origin document directly to semantic collection.
        This is the new pattern: origin → semantic (no raw_documents intermediate).
        
        Args:
            origin_document: Normalized document from OriginMongoDBSource with keys:
                - origin_id: str
                - origin_collection: str
                - origin_db: str
                - content: str
                - metadata: dict
                - updated_at: datetime or None
            skip_duplicates: If True, skip if semantic chunks already exist
            
        Returns:
            Dictionary with:
                - origin_id: The origin document ID
                - chunks_created: Number of chunks created
                - status: 'success', 'skipped', or 'failed'
                - error: Error message if failed
        """
        try:
            origin_id = origin_document.get('origin_id')
            origin_collection = origin_document.get('origin_collection')
            origin_db = origin_document.get('origin_db')
            content = origin_document.get('content', '')
            metadata = origin_document.get('metadata', {})
            
            if not origin_id:
                raise ValueError("origin_document must have 'origin_id'")
            
            print(f"[IngestionPipeline] Ingesting origin document {origin_id} to semantic collection")
            
            # Check for duplicates if skip_duplicates is enabled
            if skip_duplicates:
                if self.raw_store.has_semantic_chunks(origin_id, origin_collection, origin_db):
                    print(f"[IngestionPipeline] Document {origin_id} already has semantic chunks, skipping")
                    return {
                        'origin_id': origin_id,
                        'chunks_created': 0,
                        'status': 'skipped',
                        'reason': 'semantic_chunks_exist'
                    }
            
            # Step 1: Chunk the content
            print(f"[IngestionPipeline] Chunking document {origin_id}...")
            print(f"[IngestionPipeline] Content length: {len(content)} characters")
            chunks_data = chunk_text_with_line_numbers(content)
            
            if not chunks_data:
                raise ValueError(f"No chunks created from document {origin_id}")
            
            print(f"[IngestionPipeline] Created {len(chunks_data)} semantic chunks for document {origin_id}")
            
            # Step 2: Generate embeddings
            print(f"[IngestionPipeline] Generating embeddings for {len(chunks_data)} chunks...")
            chunk_texts = [chunk_text for chunk_text, _, _ in chunks_data]
            embeddings = self.embedding_service.generate_embeddings(chunk_texts)
            
            if len(embeddings) != len(chunks_data):
                raise ValueError(f"Embedding count mismatch: {len(embeddings)} embeddings for {len(chunks_data)} chunks")
            
            print(f"[IngestionPipeline] Generated {len(embeddings)} embeddings")
            
            # Step 3: Upsert chunks to semantic collection
            print(f"[IngestionPipeline] Storing {len(chunks_data)} chunks in semantic collection...")
            chunks_stored = 0
            for idx, ((chunk_text, line_start, line_end), embedding) in enumerate(zip(chunks_data, embeddings)):
                chunk_id = f"chunk_{idx}"
                print(f"[IngestionPipeline] Storing chunk {chunk_id} (index {idx}) for document {origin_id}, text length: {len(chunk_text)}")
                
                # Store in semantic collection
                result = self.raw_store.store_semantic_chunk_upsert(
                    origin_id=origin_id,
                    chunk_id=chunk_id,
                    chunk_text=chunk_text,
                    embedding=embedding,
                    metadata={
                        **metadata,
                        'line_start': line_start,
                        'line_end': line_end,
                        'chunk_index': idx,
                        'origin_collection': origin_collection,
                        'origin_db': origin_db
                    },
                    origin_collection_name=origin_collection,
                    origin_db_name=origin_db
                )
                chunks_stored += 1
            
            print(f"[IngestionPipeline] Successfully stored {chunks_stored} chunks for document {origin_id}")
            
            return {
                'origin_id': origin_id,
                'chunks_created': chunks_stored,
                'status': 'success'
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"[IngestionPipeline] Error ingesting origin document to semantic: {error_msg}")
            import traceback
            traceback.print_exc()
            return {
                'origin_id': origin_document.get('origin_id', 'unknown'),
                'chunks_created': 0,
                'status': 'failed',
                'error': error_msg
            }
    
    def ingest_origin_documents_batch_to_semantic(
        self,
        origin_documents: List[Dict[str, Any]],
        skip_duplicates: bool = True
    ) -> Dict[str, Any]:
        """
        Ingest multiple normalized origin documents to semantic collections.
        
        Args:
            origin_documents: List of normalized documents from OriginMongoDBSource
            skip_duplicates: If True, skip documents that already have semantic chunks
            
        Returns:
            Dictionary with:
                - total: Total number of documents attempted
                - successful: Number successfully ingested
                - skipped: Number skipped (duplicates)
                - failed: Number that failed
                - total_chunks_created: Total chunks created across all documents
                - details: List of results for each document
        """
        results = {
            'total': len(origin_documents),
            'successful': 0,
            'skipped': 0,
            'failed': 0,
            'total_chunks_created': 0,
            'details': []
        }
        
        if not origin_documents:
            return results
        
        print(f"[IngestionPipeline] Starting batch ingestion of {len(origin_documents)} documents to semantic collections")
        
        # Process each document
        for idx, origin_doc in enumerate(origin_documents, 1):
            try:
                origin_id = origin_doc.get('origin_id', f'doc_{idx}')
                print(f"[IngestionPipeline] Processing document {idx}/{len(origin_documents)}: {origin_id}")
                
                result = self.ingest_origin_document_to_semantic(
                    origin_document=origin_doc,
                    skip_duplicates=skip_duplicates
                )
                
                if result.get('status') == 'skipped':
                    results['skipped'] += 1
                    results['details'].append({
                        'origin_id': origin_id,
                        'status': 'skipped',
                        'reason': result.get('reason', 'semantic_chunks_exist')
                    })
                elif result.get('status') == 'success':
                    results['successful'] += 1
                    chunks_created = result.get('chunks_created', 0)
                    results['total_chunks_created'] += chunks_created
                    results['details'].append({
                        'origin_id': origin_id,
                        'status': 'success',
                        'chunks_created': chunks_created
                    })
                else:
                    results['failed'] += 1
                    results['details'].append({
                        'origin_id': origin_id,
                        'status': 'failed',
                        'error': result.get('error', 'Unknown error')
                    })
                    
            except Exception as e:
                results['failed'] += 1
                error_msg = str(e)
                print(f"[IngestionPipeline] Error ingesting document {origin_doc.get('origin_id', 'unknown')}: {error_msg}")
                results['details'].append({
                    'origin_id': origin_doc.get('origin_id', 'unknown'),
                    'status': 'failed',
                    'error': error_msg
                })
                # Continue processing other documents
                continue
        
        print(f"[IngestionPipeline] Batch ingestion complete: {results['successful']} successful, {results['skipped']} skipped, {results['failed']} failed, {results['total_chunks_created']} total chunks created")
        return results
    
    def close(self):
        """Close all connections."""
        if self.raw_store:
            self.raw_store.close()
        if self.vector_store:
            self.vector_store.close()

