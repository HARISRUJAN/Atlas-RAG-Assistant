"""Real-time ingestion service using MongoDB Change Streams."""

import logging
import threading
from queue import Queue
from typing import Optional, Dict, Any
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

from backend.config import Config
from backend.services.ingestion_pipeline import IngestionPipeline

logger = logging.getLogger(__name__)


class RealtimeIngestionService:
    """Service for real-time ingestion using MongoDB Change Streams."""
    
    def __init__(
        self,
        db_name: str,
        origin_collection: str,
        target_vector_collection: Optional[str] = None,
        mongodb_uri: Optional[str] = None
    ):
        """
        Initialize real-time ingestion service.
        
        Args:
            db_name: Database name containing origin collection
            origin_collection: Collection name to monitor (e.g., "movies")
            target_vector_collection: Optional target vector collection (e.g., "srugenai_db.movies")
            mongodb_uri: Optional MongoDB URI. Defaults to Config.MONGODB_URI
        """
        self.db_name = db_name
        self.origin_collection = origin_collection
        self.target_vector_collection = target_vector_collection
        self.mongodb_uri = mongodb_uri or Config.MONGODB_URI
        
        if not self.mongodb_uri:
            raise ValueError("MongoDB URI is required for RealtimeIngestionService")
        
        self.queue: Queue = Queue()
        self.watch_thread: Optional[threading.Thread] = None
        self.worker_thread: Optional[threading.Thread] = None
        self.running = False
        self.client: Optional[MongoClient] = None
        self.db = None
        self.collection = None
    
    def _connect(self):
        """Connect to MongoDB."""
        try:
            connection_params = {
                'serverSelectionTimeoutMS': 30000,
                'connectTimeoutMS': 30000,
            }
            
            if self.mongodb_uri.startswith('mongodb+srv://'):
                if 'retryWrites' not in self.mongodb_uri:
                    separator = '&' if '?' in self.mongodb_uri else '?'
                    uri_with_params = f"{self.mongodb_uri}{separator}retryWrites=true&w=majority"
                else:
                    uri_with_params = self.mongodb_uri
            else:
                uri_with_params = self.mongodb_uri
            
            self.client = MongoClient(uri_with_params, **connection_params)
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            self.collection = self.db[self.origin_collection]
            
            logger.info(f"[RealtimeIngestion] Connected to {self.db_name}.{self.origin_collection}")
        except Exception as e:
            logger.error(f"[RealtimeIngestion] Error connecting: {e}")
            raise
    
    def start(self):
        """Start the real-time ingestion service."""
        if self.running:
            logger.warning("[RealtimeIngestion] Service is already running")
            return
        
        try:
            self._connect()
            self.running = True
            
            # Start watch thread
            self.watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
            self.watch_thread.start()
            
            # Start worker thread
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            
            logger.info(f"[RealtimeIngestion] Started monitoring {self.db_name}.{self.origin_collection}")
        except Exception as e:
            logger.error(f"[RealtimeIngestion] Failed to start: {e}")
            self.running = False
            raise
    
    def stop(self):
        """Stop the real-time ingestion service."""
        if not self.running:
            return
        
        self.running = False
        
        # Wait for threads to finish (with timeout)
        if self.watch_thread:
            self.watch_thread.join(timeout=5)
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                logger.error(f"[RealtimeIngestion] Error closing client: {e}")
        
        logger.info("[RealtimeIngestion] Service stopped")
    
    def _watch_loop(self):
        """Monitor origin collection for changes."""
        try:
            # Pipeline to watch for insert and update operations
            pipeline = [
                {
                    "$match": {
                        "operationType": {"$in": ["insert", "update", "replace"]}
                    }
                }
            ]
            
            logger.info(f"[RealtimeIngestion] Starting change stream on {self.db_name}.{self.origin_collection}")
            
            with self.collection.watch(pipeline) as stream:
                for change in stream:
                    if not self.running:
                        break
                    
                    try:
                        operation_type = change.get('operationType')
                        document_key = change.get('documentKey', {})
                        doc_id = document_key.get('_id')
                        
                        if doc_id:
                            logger.info(f"[RealtimeIngestion] Detected {operation_type} for document {doc_id}")
                            self.queue.put({
                                'doc_id': doc_id,
                                'operation_type': operation_type,
                                'change': change
                            })
                    except Exception as e:
                        logger.error(f"[RealtimeIngestion] Error processing change event: {e}")
                        
        except Exception as e:
            logger.error(f"[RealtimeIngestion] Watch loop error: {e}")
            if self.running:
                # Try to restart after a delay
                import time
                time.sleep(5)
                if self.running:
                    logger.info("[RealtimeIngestion] Attempting to restart watch loop...")
                    self._watch_loop()
    
    def _worker_loop(self):
        """Process queued documents."""
        pipeline = None
        
        while self.running:
            try:
                # Get document from queue (with timeout to allow checking self.running)
                try:
                    item = self.queue.get(timeout=1)
                except:
                    continue
                
                doc_id = item.get('doc_id')
                operation_type = item.get('operation_type')
                
                if not doc_id:
                    continue
                
                try:
                    # Fetch the document
                    doc = self.collection.find_one({'_id': doc_id})
                    if not doc:
                        logger.warning(f"[RealtimeIngestion] Document {doc_id} not found after change event")
                        continue
                    
                    origin_id = str(doc.get('_id', doc_id))
                    
                    # Create ingestion pipeline if needed
                    if not pipeline:
                        pipeline = IngestionPipeline(mongodb_uri=self.mongodb_uri)
                    
                    # Build connection config
                    connection_config = {
                        'uri': self.mongodb_uri,
                        'database_name': self.db_name,
                        'collection_name': self.origin_collection
                    }
                    
                    # Ingest document (with deduplication)
                    result = pipeline.ingest_origin_document(
                        origin_source_type='mongodb',
                        origin_id=origin_id,
                        connection_config=connection_config,
                        skip_duplicates=True
                    )
                    
                    if result.get('skipped'):
                        logger.info(f"[RealtimeIngestion] Document {origin_id} already ingested, skipped")
                    else:
                        logger.info(f"[RealtimeIngestion] Successfully ingested document {origin_id}")
                        
                        # Optionally auto-process to vector collection
                        if self.target_vector_collection and result.get('raw_document_id'):
                            try:
                                process_result = pipeline.process_raw_document(
                                    result.get('raw_document_id'),
                                    target_collection=self.target_vector_collection
                                )
                                logger.info(f"[RealtimeIngestion] Processed {origin_id} to {self.target_vector_collection}")
                            except Exception as e:
                                logger.error(f"[RealtimeIngestion] Error processing {origin_id}: {e}")
                
                except Exception as e:
                    logger.error(f"[RealtimeIngestion] Error processing document {doc_id}: {e}")
                    import traceback
                    traceback.print_exc()
                
                finally:
                    self.queue.task_done()
                    
            except Exception as e:
                logger.error(f"[RealtimeIngestion] Worker loop error: {e}")
                import time
                time.sleep(1)  # Brief pause before retrying
        
        # Cleanup
        if pipeline:
            try:
                pipeline.close()
            except:
                pass


# Global service instance (can be initialized in app.py)
_realtime_service: Optional[RealtimeIngestionService] = None


def get_realtime_service() -> Optional[RealtimeIngestionService]:
    """Get the global real-time ingestion service instance."""
    return _realtime_service


def initialize_realtime_service(
    db_name: str,
    origin_collection: str,
    target_vector_collection: Optional[str] = None,
    mongodb_uri: Optional[str] = None,
    auto_start: bool = True
) -> RealtimeIngestionService:
    """
    Initialize and optionally start the real-time ingestion service.
    
    Args:
        db_name: Database name
        origin_collection: Origin collection to monitor
        target_vector_collection: Target vector collection
        mongodb_uri: MongoDB URI
        auto_start: If True, start the service immediately
        
    Returns:
        RealtimeIngestionService instance
    """
    global _realtime_service
    
    _realtime_service = RealtimeIngestionService(
        db_name=db_name,
        origin_collection=origin_collection,
        target_vector_collection=target_vector_collection,
        mongodb_uri=mongodb_uri
    )
    
    if auto_start:
        _realtime_service.start()
    
    return _realtime_service

