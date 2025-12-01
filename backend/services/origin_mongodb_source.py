"""Origin MongoDB source service for fetching documents from origin collections."""

from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from datetime import datetime
import json

from backend.config import Config


class OriginMongoDBSource:
    """
    Service for reading documents from MongoDB origin collections.
    
    This service is read-only and does not mutate the origin collection schema.
    All documents are normalized to a common shape for ingestion.
    """
    
    def __init__(
        self,
        mongodb_uri: Optional[str] = None,
        database_name: Optional[str] = None,
        collection_name: Optional[str] = None
    ):
        """
        Initialize origin MongoDB source.
        
        Args:
            mongodb_uri: MongoDB URI. Defaults to Config.MONGODB_URI
            database_name: Database name. Defaults to Config.ORIGIN_DB_NAME
            collection_name: Collection name. Defaults to Config.ORIGIN_COLLECTION_NAME
        """
        self.mongodb_uri = mongodb_uri or Config.MONGODB_URI
        self.database_name = database_name or Config.ORIGIN_DB_NAME
        self.collection_name = collection_name or Config.ORIGIN_COLLECTION_NAME
        
        if not self.mongodb_uri:
            raise ValueError("MongoDB URI is required for OriginMongoDBSource")
        if not self.database_name:
            raise ValueError("Database name is required")
        if not self.collection_name:
            raise ValueError("Collection name is required")
        
        # Validate that this is not a semantic collection
        if Config.is_semantic_collection(self.collection_name):
            raise ValueError(
                f"Collection '{self.collection_name}' is a semantic collection. "
                f"Origin source must use origin collections, not semantic collections."
            )
        
        # Configure MongoDB client
        connection_params = {
            'serverSelectionTimeoutMS': 30000,
            'connectTimeoutMS': 30000,
            'socketTimeoutMS': 30000,
        }
        
        if self.mongodb_uri.startswith('mongodb+srv://'):
            if 'retryWrites' not in self.mongodb_uri:
                separator = '&' if '?' in self.mongodb_uri else '?'
                uri_with_params = f"{self.mongodb_uri}{separator}retryWrites=true&w=majority"
            else:
                uri_with_params = self.mongodb_uri
        else:
            connection_params['tls'] = True
            connection_params['tlsAllowInvalidCertificates'] = False
            uri_with_params = self.mongodb_uri
        
        try:
            self.client = MongoClient(uri_with_params, **connection_params)
            self.client.admin.command('ping')
        except Exception as e:
            error_msg = str(e)
            if 'SSL' in error_msg or 'TLS' in error_msg:
                print("\n" + "="*70)
                print("SSL/TLS CONNECTION ERROR DETECTED")
                print("="*70)
                print("\nYour connection string should be in this format:")
                print("mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority")
                print("="*70 + "\n")
            raise
        
        self.db = self.client[self.database_name]
        self.collection = self.db[self.collection_name]
        
        print(f"[OriginMongoDBSource] Connected to {self.database_name}.{self.collection_name}")
    
    def _extract_text_content(self, doc: Dict[str, Any]) -> str:
        """
        Intelligently extract meaningful text content from a MongoDB document.
        Prioritizes text fields and excludes metadata/IDs/encrypted fields.
        
        Args:
            doc: Raw MongoDB document
            
        Returns:
            Extracted text content as string
        """
        # Fields to prioritize (in order of preference)
        # Include movie/document-specific fields for better context
        priority_fields = [
            'content', 'text', 'body', 'description', 'summary', 
            'fullplot', 'plot',  # Movie-specific: full plot description
            'title', 'name', 'display_name', 'message', 'comment', 
            'note', 'details', 'value', 'data'
        ]
        
        # Fields to exclude (metadata, IDs, encrypted, etc.)
        excluded_fields = {
            '_id', 'id', 'uuid', 'connection_id', 'raw_document_id',
            'password', 'api_key', 'secret', 'token', 'encrypted_uri',
            'encrypted_api_key', 'encrypted_password', 'encrypted_secret',
            'created_at', 'updated_at', 'createdAt', 'updatedAt',
            'timestamp', 'last_modified', 'modified_at', 'modifiedAt',
            'status', 'type', 'provider', 'scopes'
        }
        
        # Strategy 1: Collect multiple meaningful fields and combine them
        # This ensures we get name, email, text, etc. all together for better context
        meaningful_fields = []
        for field in priority_fields:
            if field in doc:
                value = doc[field]
                if value and isinstance(value, str) and len(value.strip()) > 0:
                    meaningful_fields.append(f"{field}: {value.strip()}")
                elif value and isinstance(value, (int, float)):
                    meaningful_fields.append(f"{field}: {value}")
        
        # If we found meaningful fields, combine them (don't return early for single field)
        # This ensures we get title + plot + other fields together
        if meaningful_fields:
            # For single field, still include field name for context
            # For multiple fields, combine with newlines
            if len(meaningful_fields) == 1:
                # Single field: keep the "field: value" format for context
                return meaningful_fields[0]
            else:
                # Multiple fields: combine them
                return '\n\n'.join(meaningful_fields)
        
        # Strategy 2: Find additional string fields with substantial text
        # Add to meaningful_fields if not already included
        text_parts = []
        for key, value in doc.items():
            # Skip excluded fields and priority fields (already processed)
            if key in excluded_fields or key.startswith('encrypted_') or key in priority_fields:
                continue
            
            # Skip if it's a metadata field (short strings, IDs, etc.)
            if isinstance(value, str):
                # Skip if it looks like an ID or short code
                if len(value) < 10 and (value.isalnum() or '_' in value or '-' in value):
                    continue
                # Skip if it's a timestamp format
                if any(char.isdigit() for char in value) and len(value) < 30:
                    try:
                        from dateutil import parser
                        parser.parse(value)
                        continue  # It's a date, skip it
                    except:
                        pass
                
                # Include if it's substantial text (lower threshold for additional fields)
                # Also include movie-specific fields like 'directors', 'writers' even if short
                if len(value.strip()) > 10 or key in ['directors', 'writers', 'countries', 'languages']:
                    text_parts.append(f"{key}: {value.strip()}")
            elif isinstance(value, (int, float, bool)):
                # Include simple values
                text_parts.append(f"{key}: {value}")
            elif isinstance(value, list):
                # Extract text from list items
                list_text = []
                for item in value:
                    if isinstance(item, str) and len(item.strip()) > 0:
                        # Include all list items, even short ones (like cast names, genres)
                        # This helps with queries like "movies with Tom Hanks" or "action movies"
                        list_text.append(item.strip())
                    elif isinstance(item, dict):
                        # Recursively extract from nested dicts
                        nested_text = self._extract_text_content(item)
                        if nested_text:
                            list_text.append(nested_text)
                if list_text:
                    # Format lists nicely: "cast: Actor1, Actor2, Actor3" or "genres: Drama, Action"
                    text_parts.append(f"{key}: {', '.join(list_text)}")
            elif isinstance(value, dict):
                # Recursively extract from nested objects
                nested_text = self._extract_text_content(value)
                if nested_text and len(nested_text) > 20:
                    text_parts.append(f"{key}: {nested_text}")
        
        # Strategy 3: Combine meaningful fields with additional text parts
        if meaningful_fields:
            all_parts = meaningful_fields + text_parts
            return '\n\n'.join(all_parts)
        elif text_parts:
            return '\n\n'.join(text_parts)
        
        # Strategy 4: Last resort - filtered JSON dump (exclude metadata fields)
        doc_copy = {}
        for key, value in doc.items():
            if key in excluded_fields or key.startswith('encrypted_'):
                continue
            # Only include if it's a simple type or contains text
            if isinstance(value, (str, int, float, bool)):
                if isinstance(value, str) and len(value.strip()) > 0:
                    doc_copy[key] = value
                elif not isinstance(value, str):
                    doc_copy[key] = value
            elif isinstance(value, (list, dict)) and len(str(value)) < 200:
                # Include small arrays/objects
                doc_copy[key] = value
        
        if doc_copy:
            return json.dumps(doc_copy, indent=2, default=str, ensure_ascii=False)
        
        # Fallback: empty string if nothing meaningful found
        return ''
    
    def _normalize_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a MongoDB document to common shape for ingestion.
        Intelligently extracts meaningful text content from JSON documents.
        
        Args:
            doc: Raw MongoDB document
            
        Returns:
            Normalized document with standard fields
        """
        # Extract origin_id (convert ObjectId to string if needed)
        origin_id = str(doc.get('_id', ''))
        
        # Extract content - intelligently find meaningful text fields
        content = self._extract_text_content(doc)
        
        # Extract metadata (all fields except _id, content, text, body)
        metadata = {
            k: v for k, v in doc.items() 
            if k not in ['_id', 'content', 'text', 'body']
        }
        
        # Extract updated_at timestamp
        # Try multiple strategies to find a timestamp
        updated_at = None
        
        # Strategy 1: Try common timestamp field names
        for field_name in ['updated_at', 'updatedAt', 'last_modified', 'modified_at', 'modifiedAt']:
            if field_name in doc:
                updated_at = doc[field_name]
                break
        
        # Strategy 2: Use _id ObjectId timestamp as fallback
        if updated_at is None and '_id' in doc:
            from bson import ObjectId
            try:
                obj_id = doc['_id']
                if isinstance(obj_id, ObjectId):
                    # ObjectId contains timestamp in first 4 bytes
                    updated_at = obj_id.generation_time
                elif isinstance(obj_id, datetime):
                    updated_at = obj_id
            except:
                pass
        
        # Strategy 3: Use created_at if available
        if updated_at is None:
            for field_name in ['created_at', 'createdAt', 'timestamp']:
                if field_name in doc:
                    updated_at = doc[field_name]
                    break
        
        # Ensure updated_at is datetime or None
        if updated_at and not isinstance(updated_at, datetime):
            try:
                if isinstance(updated_at, str):
                    from dateutil import parser
                    updated_at = parser.parse(updated_at)
                elif hasattr(updated_at, 'timestamp'):  # Handle other datetime-like objects
                    # Convert to datetime if possible
                    pass
                else:
                    updated_at = None
            except Exception as parse_error:
                print(f"[OriginMongoDBSource] Could not parse timestamp field: {parse_error}")
                updated_at = None
        
        return {
            'origin_id': origin_id,
            'origin_collection': self.collection_name,
            'origin_db': self.database_name,
            'content': content or '',
            'metadata': metadata,
            'updated_at': updated_at
        }
    
    def fetch_document_by_id(self, origin_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single document by origin_id.
        
        Args:
            origin_id: Document ID in the origin collection
            
        Returns:
            Normalized document or None if not found
        """
        try:
            from bson import ObjectId
            try:
                doc_id = ObjectId(origin_id)
            except:
                doc_id = origin_id
            
            doc = self.collection.find_one({'_id': doc_id})
            if not doc:
                return None
            
            return self._normalize_document(doc)
        except Exception as e:
            print(f"[OriginMongoDBSource] Error fetching document {origin_id}: {e}")
            return None
    
    def fetch_all_documents(self, limit: Optional[int] = None, skip: int = 0) -> List[Dict[str, Any]]:
        """
        Fetch all documents from the origin collection.
        
        Args:
            limit: Optional limit on number of documents
            skip: Number of documents to skip
            
        Returns:
            List of normalized documents
        """
        try:
            cursor = self.collection.find({})
            if skip > 0:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)
            
            documents = []
            for doc in cursor:
                try:
                    normalized = self._normalize_document(doc)
                    documents.append(normalized)
                except Exception as e:
                    print(f"[OriginMongoDBSource] Error normalizing document {doc.get('_id', 'unknown')}: {e}")
                    continue
            
            print(f"[OriginMongoDBSource] Fetched {len(documents)} documents from {self.database_name}.{self.collection_name}")
            return documents
        except Exception as e:
            print(f"[OriginMongoDBSource] Error fetching all documents: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def fetch_new_documents(self, since_timestamp: datetime, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch documents that have been updated since the given timestamp.
        
        Uses multiple strategies:
        1. Try timestamp fields (updated_at, updatedAt, last_modified)
        2. Fallback to _id ObjectId timestamp if available
        3. If no timestamp strategy works, fetch all documents (with warning)
        
        Args:
            since_timestamp: Timestamp to fetch documents after
            limit: Optional limit on number of documents
            
        Returns:
            List of normalized documents
        """
        try:
            # Strategy 1: Try timestamp fields first
            query = {
                '$or': [
                    {'updated_at': {'$gte': since_timestamp}},
                    {'updatedAt': {'$gte': since_timestamp}},
                    {'last_modified': {'$gte': since_timestamp}},
                ]
            }
            
            # Check if any documents have timestamp fields
            sample_doc = self.collection.find_one({
                '$or': [
                    {'updated_at': {'$exists': True}},
                    {'updatedAt': {'$exists': True}},
                    {'last_modified': {'$exists': True}}
                ]
            })
            
            if sample_doc:
                # Use timestamp-based query
                cursor = self.collection.find(query).sort('updated_at', 1)
                if limit:
                    cursor = cursor.limit(limit)
            else:
                # Strategy 2: Fallback to _id ObjectId timestamp
                # MongoDB ObjectIds contain timestamp in first 4 bytes
                from bson import ObjectId
                try:
                    # Create ObjectId from timestamp (approximate)
                    # ObjectId timestamp is seconds since epoch
                    timestamp_seconds = int(since_timestamp.timestamp())
                    min_object_id = ObjectId.from_datetime(since_timestamp)
                    
                    # Query by _id >= min_object_id (documents created/updated after timestamp)
                    query = {'_id': {'$gte': min_object_id}}
                    cursor = self.collection.find(query).sort('_id', 1)
                    if limit:
                        cursor = cursor.limit(limit)
                    
                    print(f"[OriginMongoDBSource] Using _id ObjectId timestamp fallback (no timestamp fields found)")
                except Exception as oid_error:
                    # Strategy 3: If ObjectId fallback fails, fetch all with warning
                    print(f"[OriginMongoDBSource] WARNING: No timestamp fields found and ObjectId fallback failed: {oid_error}")
                    print(f"[OriginMongoDBSource] Falling back to fetching all documents (since_timestamp ignored)")
                    cursor = self.collection.find({}).sort('_id', 1)
                    if limit:
                        cursor = cursor.limit(limit)
            
            documents = []
            for doc in cursor:
                try:
                    normalized = self._normalize_document(doc)
                    documents.append(normalized)
                except Exception as e:
                    print(f"[OriginMongoDBSource] Error normalizing document {doc.get('_id', 'unknown')}: {e}")
                    continue
            
            print(f"[OriginMongoDBSource] Fetched {len(documents)} new documents since {since_timestamp}")
            return documents
        except Exception as e:
            print(f"[OriginMongoDBSource] Error fetching new documents: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def close(self):
        """Close MongoDB connection."""
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                print(f"[OriginMongoDBSource] Error closing client: {e}")

