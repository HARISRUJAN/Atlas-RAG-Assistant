"""Unified vector store service that routes to multiple providers."""

from typing import List, Dict, Any, Optional
from backend.models.connection import Connection, ConnectionStorage
from backend.services.providers import (
    MongoDBProvider, RedisProvider, QdrantProvider, PineconeProvider
)
from backend.models.document import DocumentChunk


class UnifiedVectorStore:
    """Unified vector store that routes queries to appropriate providers."""
    
    def __init__(self, connection_ids: List[str], collection_names: Optional[List[str]] = None):
        """
        Initialize unified vector store.
        
        Args:
            connection_ids: List of connection IDs to use
            collection_names: Optional list of collection names (format: "connection_id:collection_name")
        """
        self.connection_ids = connection_ids
        self.collection_names = collection_names or []
        self.storage = ConnectionStorage()
        self.providers = {}
    
    def _extract_mongodb_kwargs(self, connection_id: str, collection_names: List[str]) -> Dict[str, Any]:
        """
        Extract MongoDB-specific kwargs from collection names.
        
        Args:
            connection_id: Connection ID
            collection_names: List of collection names for this connection
            
        Returns:
            Dictionary with database_name, collection_name, index_name if extractable
        """
        kwargs = {}
        
        if not collection_names:
            return kwargs
        
        # Extract common database from collection names if they're in "database.collection" format
        databases = set()
        collections = set()
        
        for coll_name in collection_names:
            if '.' in coll_name:
                db_name, coll_name_only = coll_name.split('.', 1)
                databases.add(db_name)
                collections.add(coll_name_only)
        
        # If all collections share the same database, use it as default
        if len(databases) == 1:
            kwargs['database_name'] = list(databases)[0]
            print(f"[UnifiedVectorStore] Extracted database_name='{kwargs['database_name']}' for connection {connection_id}")
        
        # If all collections are the same, use it as default collection
        if len(collections) == 1 and len(databases) <= 1:
            kwargs['collection_name'] = list(collections)[0]
            print(f"[UnifiedVectorStore] Extracted collection_name='{kwargs['collection_name']}' for connection {connection_id}")
        
        return kwargs
    
    def _get_provider(self, connection: Connection, collection_names: Optional[List[str]] = None) -> Any:
        """
        Get or create provider instance for connection.
        
        Args:
            connection: Connection instance
            collection_names: Optional list of collection names for this connection (used to extract provider-specific kwargs)
            
        Returns:
            Provider instance
        """
        if connection.connection_id not in self.providers:
            providers_map = {
                'mongo': MongoDBProvider,
                'redis': RedisProvider,
                'qdrant': QdrantProvider,
                'pinecone': PineconeProvider
            }
            
            ProviderClass = providers_map.get(connection.provider)
            if not ProviderClass:
                raise ValueError(f"Unknown provider: {connection.provider}")
            
            # Extract provider-specific kwargs from collection names if available
            provider_kwargs = {}
            if connection.provider == 'mongo' and collection_names:
                provider_kwargs = self._extract_mongodb_kwargs(connection.connection_id, collection_names)
            
            # For Pinecone, extract index_name if available
            if connection.provider == 'pinecone' and collection_names and len(collection_names) == 1:
                # If single collection name provided, use it as index_name
                provider_kwargs['index_name'] = collection_names[0]
            
            # For Qdrant, collection names are handled at search time
            # For Redis, index_name can be extracted similarly
            
            self.providers[connection.connection_id] = ProviderClass(
                uri=connection.uri,
                api_key=connection.api_key,
                **provider_kwargs
            )
        
        return self.providers[connection.connection_id]
    
    def _parse_collection_mapping(self) -> Dict[str, List[str]]:
        """
        Parse collection names to map connection_id -> collection_names.
        
        Supports formats:
        - "connection_id:collection_name" - specific connection and collection
        - "database.collection" - database.collection format (for MongoDB)
        - "collection_name" - plain collection name (applied to all connections)
        
        Returns:
            Dictionary mapping connection_id to list of collection names
        """
        mapping = {}
        
        print(f"[UnifiedVectorStore] Parsing {len(self.collection_names)} collection name(s)")
        
        for coll_spec in self.collection_names:
            print(f"[UnifiedVectorStore] Processing collection spec: '{coll_spec}'")
            
            if ':' in coll_spec:
                # Format: "connection_id:collection_name"
                parts = coll_spec.split(':', 1)
                conn_id = parts[0]
                coll_name = parts[1]
                
                # Validate connection_id exists
                if conn_id not in self.connection_ids:
                    print(f"[UnifiedVectorStore] WARNING: Connection ID '{conn_id}' not in connection_ids list")
                    continue
                
                if conn_id not in mapping:
                    mapping[conn_id] = []
                mapping[conn_id].append(coll_name)
                print(f"[UnifiedVectorStore] Mapped '{coll_name}' to connection '{conn_id}'")
            elif '.' in coll_spec:
                # Format: "database.collection" - MongoDB format
                # For MongoDB connections, we need to extract just the collection name
                # or pass the full "database.collection" format
                db_name, coll_name = coll_spec.split('.', 1)
                print(f"[UnifiedVectorStore] Detected database.collection format: db='{db_name}', coll='{coll_name}'")
                
                # Apply to all MongoDB connections (or all connections if provider unknown)
                for conn_id in self.connection_ids:
                    try:
                        connection = self.storage.get(conn_id)
                        if connection and connection.provider == 'mongo':
                            # For MongoDB, we can use either format
                            # Try collection name first, fallback to full path
                            if conn_id not in mapping:
                                mapping[conn_id] = []
                            # Store as "database.collection" for MongoDB provider to parse
                            mapping[conn_id].append(coll_spec)
                            print(f"[UnifiedVectorStore] Mapped '{coll_spec}' to MongoDB connection '{conn_id}'")
                    except Exception as e:
                        print(f"[UnifiedVectorStore] Error checking connection {conn_id}: {e}")
                        # If we can't check, add to all connections
                        if conn_id not in mapping:
                            mapping[conn_id] = []
                        mapping[conn_id].append(coll_spec)
            else:
                # Format: "collection_name" - plain collection name, use with all connections
                print(f"[UnifiedVectorStore] Plain collection name '{coll_spec}', applying to all connections")
                for conn_id in self.connection_ids:
                    if conn_id not in mapping:
                        mapping[conn_id] = []
                    mapping[conn_id].append(coll_spec)
        
        # If no collections specified, use all connections without collection filter
        if not mapping:
            print(f"[UnifiedVectorStore] No collections specified, searching all/default collections")
            for conn_id in self.connection_ids:
                mapping[conn_id] = []
        
        print(f"[UnifiedVectorStore] Final collection mapping: {mapping}")
        return mapping
    
    def vector_search(
        self,
        query_embedding: List[float],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Perform vector search across all providers.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results per provider (total may be more)
            
        Returns:
            List of results from all providers, sorted by score
        """
        all_results = []
        collection_mapping = self._parse_collection_mapping()
        errors = []
        
        print(f"[UnifiedVectorStore] Starting search across {len(self.connection_ids)} connection(s)")
        print(f"[UnifiedVectorStore] Query embedding dimension: {len(query_embedding)}")
        print(f"[UnifiedVectorStore] Requested top_k: {top_k}")
        
        for connection_id in self.connection_ids:
            try:
                # Get connection
                connection = self.storage.get(connection_id)
                if not connection:
                    error_msg = f"Connection {connection_id} not found"
                    print(f"[UnifiedVectorStore] ERROR: {error_msg}")
                    errors.append(error_msg)
                    continue
                
                print(f"[UnifiedVectorStore] Searching connection {connection_id} (provider: {connection.provider})")
                
                # Get collections for this connection
                collections = collection_mapping.get(connection_id, [])
                
                # Get provider (pass collections to extract provider-specific kwargs)
                provider = self._get_provider(connection, collection_names=collections)
                print(f"[UnifiedVectorStore] Collections for connection {connection_id}: {collections if collections else 'all/default'}")
                
                if collections:
                    # Search specific collections
                    for coll_name in collections:
                        try:
                            print(f"[UnifiedVectorStore] Searching collection '{coll_name}' in connection {connection_id}")
                            
                            # Validate collection exists (for MongoDB provider)
                            if connection.provider == 'mongo':
                                try:
                                    # Try to get provider and check if collection exists
                                    test_provider = self._get_provider(connection, collection_names=collections)
                                    available_collections = test_provider.list_collections()
                                    
                                    # Check if collection exists (handle both "collection" and "database.collection" formats)
                                    collection_exists = False
                                    if '.' in coll_name:
                                        # database.collection format
                                        collection_exists = coll_name in available_collections
                                    else:
                                        # Just collection name - check if it exists in any database
                                        collection_exists = any(coll_name in coll or coll.endswith(f'.{coll_name}') for coll in available_collections)
                                    
                                    if not collection_exists and available_collections:
                                        print(f"[UnifiedVectorStore] WARNING: Collection '{coll_name}' not found in available collections: {available_collections[:5]}...")
                                        # Continue anyway - might be a valid collection that wasn't listed
                                except Exception as e:
                                    print(f"[UnifiedVectorStore] Could not validate collection existence: {e}")
                            
                            results = provider.vector_search(
                                query_embedding=query_embedding,
                                top_k=top_k,
                                collection_name=coll_name
                            )
                            print(f"[UnifiedVectorStore] Collection '{coll_name}' returned {len(results)} results")
                            
                            # Validate results have content
                            if results:
                                empty_results = [r for r in results if not r.get('content')]
                                if empty_results:
                                    print(f"[UnifiedVectorStore] WARNING: {len(empty_results)} results from '{coll_name}' have empty content")
                            
                            # Add connection info to results
                            for result in results:
                                result['connection_id'] = connection_id
                                result['provider'] = connection.provider
                            all_results.extend(results)
                        except Exception as e:
                            error_msg = f"Error searching collection '{coll_name}' in connection {connection_id}: {str(e)}"
                            print(f"[UnifiedVectorStore] ERROR: {error_msg}")
                            errors.append(error_msg)
                            import traceback
                            traceback.print_exc()
                else:
                    # Search all collections (or default)
                    try:
                        print(f"[UnifiedVectorStore] Searching all/default collections in connection {connection_id}")
                        results = provider.vector_search(
                            query_embedding=query_embedding,
                            top_k=top_k
                        )
                        print(f"[UnifiedVectorStore] Connection {connection_id} returned {len(results)} results")
                        # Add connection info to results
                        for result in results:
                            result['connection_id'] = connection_id
                            result['provider'] = connection.provider
                        all_results.extend(results)
                    except Exception as e:
                        error_msg = f"Error searching connection {connection_id}: {str(e)}"
                        print(f"[UnifiedVectorStore] ERROR: {error_msg}")
                        errors.append(error_msg)
                        import traceback
                        traceback.print_exc()
                    
            except Exception as e:
                import traceback
                error_msg = f"Error processing connection {connection_id}: {str(e)}"
                print(f"[UnifiedVectorStore] ERROR: {error_msg}")
                errors.append(error_msg)
                traceback.print_exc()
                continue
        
        print(f"[UnifiedVectorStore] Total results before sorting: {len(all_results)}")
        if errors:
            print(f"[UnifiedVectorStore] Errors encountered: {len(errors)}")
            for err in errors:
                print(f"[UnifiedVectorStore]   - {err}")
        
        # Sanitize results before sorting to ensure consistent field structure
        all_results = self._sanitize_results(all_results)
        
        # Sort by score (descending) and return top_k overall
        all_results.sort(key=lambda x: x.get('score', 0.0), reverse=True)
        final_results = all_results[:top_k]
        print(f"[UnifiedVectorStore] Final results after sorting and limiting: {len(final_results)}")
        
        # Log sample result to verify fields
        if final_results:
            sample = final_results[0]
            print(f"[UnifiedVectorStore] Sample final result fields: {list(sample.keys())}")
            print(f"[UnifiedVectorStore] Sample file_name: '{sample.get('file_name')}', "
                  f"line_start: {sample.get('line_start')}, line_end: {sample.get('line_end')}, "
                  f"content_length: {len(sample.get('content', ''))}")
        
        return final_results
    
    def store_chunks(
        self,
        chunks: List[DocumentChunk],
        connection_id: Optional[str] = None,
        collection_name: Optional[str] = None
    ) -> int:
        """
        Store chunks in specified connection.
        
        Args:
            chunks: List of document chunks
            connection_id: Connection ID to store in (uses first if not specified)
            collection_name: Optional collection name
            
        Returns:
            Number of chunks stored
        """
        if not chunks:
            return 0
        
        # Use first connection if not specified
        target_connection_id = connection_id or (self.connection_ids[0] if self.connection_ids else None)
        if not target_connection_id:
            raise ValueError("No connection specified for storing chunks")
        
        try:
            # Get connection
            connection = self.storage.get(target_connection_id)
            if not connection:
                raise ValueError(f"Connection not found: {target_connection_id}")
            
            # Get provider (pass collection_name if available to extract kwargs)
            collection_names_for_provider = [collection_name] if collection_name else []
            provider = self._get_provider(connection, collection_names=collection_names_for_provider)
            
            # Store chunks
            count = provider.store_chunks(chunks, collection_name=collection_name)
            
            return count
            
        except Exception as e:
            print(f"Error storing chunks: {e}")
            return 0
    
    def _sanitize_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sanitize search results to ensure all required fields have valid defaults.
        Filters out results without required fields (like content).
        
        Args:
            results: List of search results from providers
            
        Returns:
            Sanitized list of search results with all required fields
        """
        sanitized = []
        for result in results:
            # Check if result has content (required field)
            has_content = result.get('content') and (
                not isinstance(result.get('content'), str) or 
                result.get('content', '').strip() != ''
            )
            
            if not has_content:
                print(f"[UnifiedVectorStore] Skipping result without content: chunk_id={result.get('chunk_id')}")
                continue
            
            # Ensure all required fields exist with proper defaults
            sanitized_result = {
                'chunk_id': result.get('chunk_id', ''),
                'document_id': result.get('document_id', ''),
                'file_name': result.get('file_name') or 'Unknown',
                'content': result.get('content', ''),
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
            
            # Copy any additional fields (like connection_id, provider)
            for key, value in result.items():
                if key not in sanitized_result:
                    sanitized_result[key] = value
            
            sanitized.append(sanitized_result)
        
        if len(sanitized) < len(results):
            print(f"[UnifiedVectorStore] Sanitized {len(sanitized)} results from {len(results)} (filtered {len(results) - len(sanitized)} invalid results)")
        
        return sanitized
    
    def list_collections(self) -> Dict[str, List[str]]:
        """
        List collections for all connections.
        
        Returns:
            Dictionary mapping connection_id to list of collections
        """
        result = {}
        
        for connection_id in self.connection_ids:
            try:
                connection = self.storage.get(connection_id)
                if not connection:
                    continue
                
                # For list_collections, we don't have specific collection names, so pass empty list
                provider = self._get_provider(connection, collection_names=[])
                collections = provider.list_collections()
                result[connection_id] = collections
                
            except Exception as e:
                print(f"Error listing collections for {connection_id}: {e}")
                result[connection_id] = []
        
        return result
    
    def close(self):
        """Close all provider connections."""
        for provider in self.providers.values():
            try:
                provider.close()
            except:
                pass
        self.storage.close()

