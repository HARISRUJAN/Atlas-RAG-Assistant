"""RAG service for orchestrating retrieval and generation."""

import requests
from typing import List, Optional
from backend.config import Config
from backend.models.query import QueryRequest, QueryResponse, SourceReference
from backend.services.embedding_service import EmbeddingService
from backend.services.vector_store import VectorStoreService
from backend.services.vector_data_store import VectorDataStore
from backend.services.unified_vector_store import UnifiedVectorStore


class RAGService:
    """Service for Retrieval-Augmented Generation."""
    
    @staticmethod
    def _ensure_semantic_collection(collection_name: Optional[str]) -> Optional[str]:
        """
        Ensure collection name is a semantic collection.
        If origin collection is provided, transform it to semantic collection.
        
        Args:
            collection_name: Collection name (can be "collection" or "database.collection")
            
        Returns:
            Semantic collection name
        """
        if not collection_name:
            return None
        
        # Handle "database.collection" format
        if '.' in collection_name:
            parts = collection_name.split('.', 1)
            if len(parts) == 2:
                db_name, coll_name = parts
                # Check if collection is already semantic
                if Config.is_semantic_collection(coll_name):
                    return collection_name
                # Transform to semantic
                semantic_coll = Config.get_semantic_collection_name(coll_name)
                return f"{db_name}.{semantic_coll}"
        
        # Single collection name
        if Config.is_semantic_collection(collection_name):
            return collection_name
        
        # Transform to semantic
        return Config.get_semantic_collection_name(collection_name)
    
    def __init__(self, collection_name: str = None, collection_names: List[str] = None, database_name: str = None, index_name: str = None, mongodb_uri: str = None, connection_ids: List[str] = None, use_pipeline: bool = True):
        """
        Initialize RAG service.
        
        Args:
            collection_name: Optional collection name (for backward compatibility). 
                            Can be "collection" or "database.collection" format.
                            Defaults to Config.MONGODB_COLLECTION_NAME
            collection_names: Optional list of collection names for multi-collection search.
                             Can be ["collection"] or ["database.collection"] format.
                             If provided, collection_name is ignored.
            database_name: Optional database name. If collection_name contains ".", this is ignored.
                          Defaults to Config.MONGODB_DATABASE_NAME
            index_name: Optional index name. Defaults to Config.MONGODB_VECTOR_INDEX_NAME
            mongodb_uri: Optional MongoDB URI. Defaults to Config.MONGODB_URI (backward compatibility)
            connection_ids: Optional list of connection IDs for multi-provider support
            use_pipeline: If True, use vector_data collection (new pipeline). If False, use legacy mode.
        """
        self.embedding_service = EmbeddingService()
        self.use_pipeline = use_pipeline
        
        # Use unified vector store if connection_ids provided
        if connection_ids:
            # Multi-provider mode
            self.connection_ids = connection_ids
            self.unified_store = UnifiedVectorStore(
                connection_ids=connection_ids,
                collection_names=collection_names
            )
            self.vector_stores = []
            self.vector_store = None
            self.vector_data_store = None
            self.collection_names = collection_names
        # Use new pipeline mode (vector_data collection)
        elif use_pipeline:
            # New pipeline mode: use vector_data collection
            # collection_names can contain "database.collection" format (e.g., "srugenai_db.movies")
            self.collection_names = None
            self.vector_stores = []
            self.vector_store = None
            
            # Determine which collection to use
            target_collection = None
            if collection_names and len(collection_names) == 1:
                target_collection = collection_names[0]
            elif collection_name:
                target_collection = collection_name
            
            # Ensure we're using semantic collection (transform if needed)
            target_collection = self._ensure_semantic_collection(target_collection)
            
            self.vector_data_store = VectorDataStore(
                database_name=database_name,
                collection_name=target_collection,  # Can be "collection" or "database.collection"
                index_name=index_name or Config.VECTOR_DATA_INDEX_NAME,
                mongodb_uri=mongodb_uri
            )
            print(f"[RAG Service] Using pipeline mode with semantic collection: {target_collection or 'default'}")
        # Determine which collections to use (legacy MongoDB mode)
        elif collection_names:
            # Multi-collection mode
            self.collection_names = collection_names
            self.vector_stores = []
            
            print(f"[RAG Service] Initializing multi-collection mode with {len(collection_names)} collection(s)")
            
            for coll_name in collection_names:
                # Ensure we're using semantic collection
                semantic_coll_name = self._ensure_semantic_collection(coll_name)
                print(f"[RAG Service] Setting up vector store for semantic collection: '{semantic_coll_name}' (from '{coll_name}')")
                try:
                    vector_store = VectorStoreService(
                        collection_name=semantic_coll_name,
                        database_name=database_name,
                        index_name=index_name,
                        mongodb_uri=mongodb_uri
                    )
                    
                    # Validate collection exists and has documents
                    try:
                        doc_count = vector_store.collection.count_documents({})
                        coll_full_name = f"{vector_store.db.name}.{vector_store.collection.name}"
                        print(f"[RAG Service] Collection '{coll_full_name}' has {doc_count} documents")
                        
                        if doc_count == 0:
                            print(f"[RAG Service] WARNING: Collection '{coll_full_name}' is empty")
                    except Exception as e:
                        print(f"[RAG Service] Could not validate collection '{coll_name}': {e}")
                    
                    self.vector_stores.append(vector_store)
                except Exception as e:
                    print(f"[RAG Service] ERROR: Failed to initialize vector store for '{coll_name}': {e}")
                    import traceback
                    traceback.print_exc()
                    # Continue with other collections
            
            self.vector_store = None  # Not used in multi-collection mode
            print(f"[RAG Service] Initialized {len(self.vector_stores)} vector store(s)")
        else:
            # Single collection mode (backward compatibility)
            self.collection_names = None
            self.vector_stores = []
            self.vector_store = VectorStoreService(
                collection_name=collection_name, 
                database_name=database_name,
                index_name=index_name,
                mongodb_uri=mongodb_uri
            )
        
        self.llm_api_url = Config.LLM_API_URL
        self.llm_api_key = Config.LLM_API_KEY
        self.llm_model = Config.LLM_MODEL
    
    def query(self, request: QueryRequest) -> QueryResponse:
        """
        Process a query through the RAG pipeline.
        
        Args:
            request: Query request
            
        Returns:
            Query response with answer and sources
        """
        import traceback
        
        # Step 1: Generate embedding for the query
        print(f"\n[RAG Service] Processing query: '{request.query[:100]}...'")
        try:
            query_embedding = self.embedding_service.generate_embedding(request.query)
            print(f"[RAG Service] Generated embedding: {len(query_embedding)} dimensions")
        except Exception as e:
            error_msg = f"Failed to generate query embedding: {str(e)}"
            print(f"[RAG Service] ERROR: {error_msg}")
            traceback.print_exc()
            return QueryResponse(
                answer=f"Error: {error_msg}. Please try again.",
                sources=[],
                query=request.query
            )
        
        # Step 2: Retrieve relevant chunks from vector store(s)
        search_results = []
        search_mode = None
        error_details = []
        
        # Log collection selection and search configuration
        print(f"\n{'='*70}")
        print(f"[RAG Service] SEARCH CONFIGURATION")
        print(f"{'='*70}")
        if self.collection_names:
            print(f"[RAG Service] Selected collections to search: {self.collection_names}")
        else:
            print(f"[RAG Service] No specific collections selected - searching all/default collections")
        
        if hasattr(self, 'connection_ids') and self.connection_ids:
            print(f"[RAG Service] Connection IDs: {self.connection_ids}")
        print(f"[RAG Service] Query embedding dimensions: {len(query_embedding)}")
        print(f"[RAG Service] Requested top_k: {request.top_k}")
        print(f"{'='*70}\n")
        
        try:
            if hasattr(self, 'vector_data_store') and self.vector_data_store:
                # New pipeline mode: use vector_data collection
                search_mode = "pipeline-vector-data"
                collection_full_name = f"{self.vector_data_store.database_name}.{self.vector_data_store.collection_name}"
                print(f"[RAG Service] Using pipeline mode with vector_data collection: {collection_full_name}")
                
                # Check collection status before searching
                try:
                    chunk_count = self.vector_data_store.collection.count_documents({})
                    print(f"[RAG Service] Collection '{collection_full_name}' has {chunk_count} chunks")
                    if chunk_count == 0:
                        print(f"[RAG Service] WARNING: Collection '{collection_full_name}' is empty! No data has been processed yet.")
                        print(f"[RAG Service] Please ingest and process documents first using the Data Ingestion tab.")
                except Exception as e:
                    print(f"[RAG Service] Could not check collection status: {e}")
                
                search_results = self.vector_data_store.vector_search(
                    query_embedding=query_embedding,
                    top_k=request.top_k
                )
                print(f"[RAG Service] Vector data search returned {len(search_results)} results from {collection_full_name}")
            elif hasattr(self, 'unified_store') and self.unified_store:
                # Multi-provider mode
                search_mode = "multi-provider"
                print(f"[RAG Service] Using multi-provider mode with {len(self.connection_ids)} connection(s)")
                print(f"[RAG Service] Collection names: {self.collection_names}")
                search_results = self.unified_store.vector_search(
                    query_embedding=query_embedding,
                    top_k=request.top_k
                )
                print(f"[RAG Service] Multi-provider search returned {len(search_results)} results")
            elif self.vector_stores:
                # Multi-collection mode: search across all collections and merge results
                search_mode = "multi-collection"
                print(f"[RAG Service] Using multi-collection mode with {len(self.vector_stores)} collection(s)")
                all_results = []
                for idx, vector_store in enumerate(self.vector_stores):
                    try:
                        coll_name = self.collection_names[idx] if self.collection_names and idx < len(self.collection_names) else "unknown"
                        print(f"[RAG Service] Searching collection: {coll_name}")
                        results = vector_store.vector_search(
                            query_embedding=query_embedding,
                            top_k=request.top_k
                        )
                        print(f"[RAG Service] Collection {coll_name} returned {len(results)} results")
                        all_results.extend(results)
                    except Exception as e:
                        coll_name = self.collection_names[idx] if self.collection_names and idx < len(self.collection_names) else "unknown"
                        error_msg = f"Error searching collection {coll_name}: {str(e)}"
                        print(f"[RAG Service] ERROR: {error_msg}")
                        error_details.append(error_msg)
                        traceback.print_exc()
                
                # Sort by relevance score (descending) and take top_k overall
                all_results.sort(key=lambda x: x.get('score', 0.0), reverse=True)
                search_results = all_results[:request.top_k]
                print(f"[RAG Service] Multi-collection search returned {len(search_results)} total results")
            else:
                # Single collection mode (backward compatibility)
                search_mode = "single-collection"
                coll_name = getattr(self.vector_store, 'collection', {}).name if hasattr(self.vector_store, 'collection') else "default"
                print(f"[RAG Service] Using single-collection mode: {coll_name}")
                search_results = self.vector_store.vector_search(
                    query_embedding=query_embedding,
                    top_k=request.top_k
                )
                print(f"[RAG Service] Single-collection search returned {len(search_results)} results")
        except Exception as e:
            error_msg = f"Error during vector search: {str(e)}"
            print(f"[RAG Service] ERROR: {error_msg}")
            traceback.print_exc()
            error_details.append(error_msg)
        
        # Log search results summary
        print(f"\n{'='*70}")
        print(f"[RAG Service] SEARCH RESULTS SUMMARY")
        print(f"{'='*70}")
        print(f"[RAG Service] Search mode: {search_mode}")
        print(f"[RAG Service] Total results retrieved: {len(search_results)}")
        if search_results:
            print(f"[RAG Service] Sample result keys: {list(search_results[0].keys())}")
            # Log field statistics
            fields_with_values = {}
            for result in search_results:
                for key, value in result.items():
                    if key not in fields_with_values:
                        fields_with_values[key] = {'total': 0, 'non_empty': 0}
                    fields_with_values[key]['total'] += 1
                    if value and (not isinstance(value, str) or value.strip()):
                        fields_with_values[key]['non_empty'] += 1
            print(f"[RAG Service] Field statistics:")
            for field, stats in fields_with_values.items():
                pct = (stats['non_empty'] / stats['total'] * 100) if stats['total'] > 0 else 0
                print(f"  - {field}: {stats['non_empty']}/{stats['total']} non-empty ({pct:.1f}%)")
        print(f"{'='*70}\n")
        
        # Check if we have results
        if not search_results:
            # Build detailed error message
            error_parts = [f"No results found for query: '{request.query}'"]
            error_parts.append(f"Search mode: {search_mode}")
            if self.collection_names:
                error_parts.append(f"Collections searched: {', '.join(self.collection_names)}")
            if error_details:
                error_parts.append(f"Errors encountered: {'; '.join(error_details)}")
            
            # Check if collections might be empty
            collection_status = []
            empty_collection_warning = None
            index_warning = None
            try:
                if hasattr(self, 'vector_data_store') and self.vector_data_store:
                    # Check vector_data collection
                    try:
                        count = self.vector_data_store.count_chunks()
                        db_name = self.vector_data_store.database_name
                        coll_name = self.vector_data_store.collection_name
                        full_name = f"{db_name}.{coll_name}"
                        collection_status.append(f"Vector data collection {full_name}: {count} chunks")
                        if count == 0:
                            empty_collection_warning = f"The vector collection '{full_name}' is empty. Please ingest and process documents first using the Data Ingestion tab (sample_mflix.movies → raw_documents → {full_name})."
                        else:
                            # Collection has data but no results - likely index issue
                            index_name = self.vector_data_store.index_name
                            index_warning = (
                                f"Collection has {count} chunks but vector search returned no results. "
                                f"This usually means the vector search index is missing or misconfigured.\n\n"
                                f"Please verify:\n"
                                f"1. Vector search index exists in MongoDB Atlas for '{full_name}'\n"
                                f"2. Index name matches one of: 'default', 'vector_data_index', '{index_name}'\n"
                                f"3. Index is in 'Active' status (not Building)\n"
                                f"4. Index configuration includes 'embedding' field with 384 dimensions\n\n"
                                f"To check: Run 'python setup_vector_index_for_collection.py {full_name}'"
                            )
                    except Exception as e:
                        print(f"[RAG Service] Error checking collection status: {e}")
                        pass
                elif hasattr(self, 'unified_store') and self.unified_store:
                    # Check unified store collections
                    collections_info = self.unified_store.list_collections()
                    for conn_id, colls in collections_info.items():
                        collection_status.append(f"Connection {conn_id}: {len(colls)} collections")
                elif self.vector_stores:
                    for vs in self.vector_stores:
                        try:
                            count = vs.collection.count_documents({})
                            coll_name = getattr(vs, 'collection', {}).name if hasattr(vs, 'collection') else "unknown"
                            collection_status.append(f"Collection {coll_name}: {count} documents")
                        except:
                            pass
                elif hasattr(self, 'vector_store') and self.vector_store:
                    try:
                        count = self.vector_store.collection.count_documents({})
                        coll_name = getattr(self.vector_store, 'collection', {}).name if hasattr(self.vector_store, 'collection') else "default"
                        collection_status.append(f"Collection {coll_name}: {count} documents")
                    except:
                        pass
            except Exception as e:
                print(f"[RAG Service] Could not check collection status: {e}")
            
            if collection_status:
                error_parts.append(f"Collection status: {'; '.join(collection_status)}")
            
            detailed_error = ". ".join(error_parts)
            if empty_collection_warning:
                detailed_error = f"{empty_collection_warning} {detailed_error}"
            if index_warning:
                detailed_error = f"{index_warning}\n\n{detailed_error}"
            print(f"[RAG Service] {detailed_error}")
            
            # Return informative error message
            user_message = "I don't have enough information to answer this question."
            if Config.FLASK_DEBUG:
                user_message += f" Debug: {detailed_error}"
            else:
                if index_warning:
                    user_message += f"\n\n{index_warning}"
                elif any("0 documents" in status or "0 chunks" in status for status in collection_status):
                    user_message += " The selected collections appear to be empty. Please upload documents first."
                elif error_details:
                    user_message += " There was an error searching the database. Please check your connection and try again."
                else:
                    user_message += " Please upload relevant documents first."
            
            return QueryResponse(
                answer=user_message,
                sources=[],
                query=request.query
            )
        
        # Step 3: Sanitize search results before using them
        search_results = self._sanitize_search_results(search_results)
        
        # Step 4: Format context from retrieved chunks
        context = self._format_context(search_results)
        
        # Step 5: Generate answer using LLM
        answer = self._generate_answer(request.query, context)
        
        # Step 6: Create source references
        sources = self._create_source_references(search_results)
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            query=request.query
        )
    
    def _sanitize_search_results(self, search_results: List[dict]) -> List[dict]:
        """
        Sanitize search results to ensure all required fields have valid defaults.
        
        Args:
            search_results: List of search results
            
        Returns:
            Sanitized list of search results
        """
        sanitized = []
        for result in search_results:
            # Ensure all required fields exist with proper defaults
            sanitized_result = {
                'chunk_id': result.get('chunk_id', ''),
                'document_id': result.get('document_id', ''),
                'file_name': result.get('file_name') or 'Unknown',
                'content': result.get('content') or result.get('chunk_text') or '',
                'line_start': result.get('line_start') or 0,
                'line_end': result.get('line_end') or 0,
                'metadata': result.get('metadata') or {},
                'score': result.get('score') or 0.0
            }
            
            # Handle empty strings
            if isinstance(sanitized_result['file_name'], str) and sanitized_result['file_name'].strip() == '':
                sanitized_result['file_name'] = 'Unknown'
            
            # Ensure numeric fields are proper types
            try:
                sanitized_result['line_start'] = int(sanitized_result['line_start'])
            except (ValueError, TypeError):
                sanitized_result['line_start'] = 0
            
            try:
                sanitized_result['line_end'] = int(sanitized_result['line_end'])
            except (ValueError, TypeError):
                sanitized_result['line_end'] = 0
            
            try:
                sanitized_result['score'] = float(sanitized_result['score'])
            except (ValueError, TypeError):
                sanitized_result['score'] = 0.0
            
            # Try to extract file_name from metadata if missing
            if sanitized_result['file_name'] == 'Unknown' and sanitized_result['metadata']:
                meta = sanitized_result['metadata']
                if isinstance(meta, dict):
                    file_name = meta.get('file_name') or meta.get('filename')
                    if file_name and isinstance(file_name, str) and file_name.strip():
                        sanitized_result['file_name'] = file_name
            
            # Copy any additional fields
            for key, value in result.items():
                if key not in sanitized_result:
                    sanitized_result[key] = value
            
            sanitized.append(sanitized_result)
        
        return sanitized
    
    def _format_context(self, search_results: List[dict]) -> str:
        """
        Format search results into context string.
        
        Args:
            search_results: List of search results
            
        Returns:
            Formatted context string
        """
        context_parts = []
        for idx, result in enumerate(search_results, 1):
            file_name = result.get('file_name', 'Unknown')
            line_start = result.get('line_start', 0)
            line_end = result.get('line_end', 0)
            content = result.get('content') or result.get('chunk_text') or ''
            
            context_parts.append(
                f"[Source {idx}: {file_name}, lines {line_start}-{line_end}]\n{content}\n"
            )
        
        return "\n".join(context_parts)
    
    def _generate_answer(self, query: str, context: str) -> str:
        """
        Generate answer using LLM.
        
        Args:
            query: User query
            context: Context from retrieved documents
            
        Returns:
            Generated answer
        """
        # Create prompt
        prompt = self._create_prompt(query, context)
        
        try:
            # Call Llama 3.2 API (Ollama format)
            response = requests.post(
                self.llm_api_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.llm_api_key}"
                },
                json={
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                    "max_tokens": 500
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                # Extract answer from response
                answer = result.get('response', result.get('choices', [{}])[0].get('text', ''))
                return answer.strip()
            else:
                return f"Error generating answer: {response.status_code} - {response.text}"
                
        except requests.exceptions.RequestException as e:
            return f"Error connecting to LLM: {str(e)}"
    
    def _create_prompt(self, query: str, context: str) -> str:
        """
        Create prompt for LLM.
        
        Args:
            query: User query
            context: Retrieved context
            
        Returns:
            Formatted prompt
        """
        prompt = f"""You are a helpful AI assistant. Answer the question based on the provided context. 
If you cannot answer based on the context, say so clearly.

Context:
{context}

Question: {query}

Answer: Provide a clear, concise answer based on the context above. If you reference information from the context, be specific about which source it comes from."""
        
        return prompt
    
    def _create_source_references(self, search_results: List[dict]) -> List[SourceReference]:
        """
        Create source references from search results.
        
        Args:
            search_results: List of search results
            
        Returns:
            List of source references
        """
        sources = []
        
        # Log first result structure for debugging
        if search_results:
            first_result = search_results[0]
            print(f"[RAG Service] Sample search result fields: {list(first_result.keys())}")
            print(f"[RAG Service] Sample result values: file_name='{first_result.get('file_name')}', "
                  f"line_start={first_result.get('line_start')}, line_end={first_result.get('line_end')}, "
                  f"content_length={len(first_result.get('content') or first_result.get('chunk_text') or '')}")
        
        for idx, result in enumerate(search_results):
            # Helper function to safely extract field with proper default handling
            def safe_get(key: str, default: any) -> any:
                """Get field value, treating empty strings as missing."""
                value = result.get(key, default)
                # If value is empty string, treat as missing and use default
                if isinstance(value, str) and value.strip() == '':
                    return default
                return value if value is not None else default
            
            # Extract fields with proper handling for empty strings
            file_name = safe_get('file_name', 'Unknown')
            line_start = safe_get('line_start', 0)
            line_end = safe_get('line_end', 0)
            content = safe_get('content', '')
            score = safe_get('score', 0.0)
            
            # Ensure line_start and line_end are integers
            try:
                line_start = int(line_start) if line_start else 0
            except (ValueError, TypeError):
                line_start = 0
            
            try:
                line_end = int(line_end) if line_end else 0
            except (ValueError, TypeError):
                line_end = 0
            
            # Ensure score is float
            try:
                score = float(score) if score else 0.0
            except (ValueError, TypeError):
                score = 0.0
            
            # If file_name is still Unknown, try to get from metadata
            if file_name == 'Unknown' and result.get('metadata'):
                metadata = result.get('metadata', {})
                if isinstance(metadata, dict):
                    file_name = metadata.get('file_name') or metadata.get('filename') or 'Unknown'
                    # Handle empty string in metadata too
                    if isinstance(file_name, str) and file_name.strip() == '':
                        file_name = 'Unknown'
            
            # If still Unknown, try document_id as fallback
            if file_name == 'Unknown':
                doc_id = safe_get('document_id', '')
                if doc_id and doc_id != 'Unknown':
                    file_name = f"Document: {doc_id[:30]}"
            
            # Truncate content for preview
            content_preview = content[:200] + "..." if len(content) > 200 else content
            
            source = SourceReference(
                file_name=file_name,
                line_start=line_start,
                line_end=line_end,
                content=content_preview,
                relevance_score=score
            )
            sources.append(source)
            
            # Log if we had to use defaults
            if result.get('file_name') in [None, '', 'Unknown']:
                print(f"[RAG Service] WARNING: Result {idx} missing file_name, using: {file_name}")
        
        print(f"[RAG Service] Created {len(sources)} source references")
        return sources

