"""Collection service helpers for validation and metadata."""

from typing import Optional
from pymongo import MongoClient
from backend.config import Config


def is_raw_document_collection(collection_name: str) -> bool:
    """
    Check if a collection name represents a raw document store.
    
    Args:
        collection_name: Collection name in format "collection" or "database.collection"
        
    Returns:
        True if collection contains "raw_documents"
    """
    return "raw_documents" in collection_name.lower()


def has_vector_index(collection_name: str, mongodb_uri: Optional[str] = None) -> bool:
    """
    Check if a collection has a vector search index by attempting a test vector search.
    
    Note: Atlas Vector Search indexes are managed separately from regular indexes,
    so we test by attempting a vector search query.
    
    Args:
        collection_name: Collection name in format "collection" or "database.collection"
        mongodb_uri: Optional MongoDB URI. Defaults to Config.MONGODB_URI
        
    Returns:
        True if collection has a working vector index
    """
    try:
        # Parse database.collection format
        if '.' in collection_name:
            parts = collection_name.split('.', 1)
            db_name = parts[0]
            coll_name = parts[1]
        else:
            # Use default database from config
            db_name = Config.VECTOR_DATA_DATABASE_NAME or Config.MONGODB_DATABASE_NAME
            coll_name = collection_name
        
        # Connect to MongoDB
        uri = mongodb_uri or Config.MONGODB_URI
        if not uri:
            print(f"[CollectionService] No MongoDB URI provided, cannot check vector index")
            return False
        
        connection_params = {
            'serverSelectionTimeoutMS': 10000,
            'connectTimeoutMS': 10000,
        }
        
        if uri.startswith('mongodb+srv://'):
            if 'retryWrites' not in uri:
                separator = '&' if '?' in uri else '?'
                uri_with_params = f"{uri}{separator}retryWrites=true&w=majority"
            else:
                uri_with_params = uri
        else:
            uri_with_params = uri
        
        client = MongoClient(uri_with_params, **connection_params)
        
        try:
            db = client[db_name]
            collection = db[coll_name]
            
            # First, check if collection has documents with embeddings
            sample_doc = collection.find_one({"embedding": {"$exists": True}})
            if not sample_doc or 'embedding' not in sample_doc:
                print(f"[CollectionService] Collection '{db_name}.{coll_name}' has no documents with embeddings")
                client.close()
                return False
            
            embedding = sample_doc.get('embedding')
            if not isinstance(embedding, list) or len(embedding) == 0:
                print(f"[CollectionService] Collection '{db_name}.{coll_name}' has invalid embeddings")
                client.close()
                return False
            
            # Try to perform a test vector search to verify index exists
            # This is the most reliable way to check for Atlas Vector Search indexes
            test_pipeline = [
                {
                    "$vectorSearch": {
                        "index": "default",  # Default index name
                        "path": "embedding",
                        "queryVector": embedding[:384],  # Use first 384 dimensions
                        "numCandidates": 1,
                        "limit": 1
                    }
                },
                {"$limit": 1}
            ]
            
            try:
                results = list(collection.aggregate(test_pipeline))
                client.close()
                return True  # Vector search worked, index exists
            except Exception as search_error:
                error_msg = str(search_error).lower()
                # Check if error is about missing index
                if 'index' in error_msg or 'vector' in error_msg:
                    print(f"[CollectionService] Vector search index not found for '{db_name}.{coll_name}'")
                    client.close()
                    return False
                else:
                    # Other error, but might indicate index exists (just query failed)
                    # Try with different index names
                    for index_name in ['default', 'vector_index', 'vectorIndex']:
                        try:
                            test_pipeline[0]['$vectorSearch']['index'] = index_name
                            list(collection.aggregate(test_pipeline))
                            client.close()
                            return True
                        except:
                            continue
                    client.close()
                    return False
            
        except Exception as e:
            print(f"[CollectionService] Error checking vector index for {db_name}.{coll_name}: {e}")
            client.close()
            return False
            
    except Exception as e:
        print(f"[CollectionService] Error connecting to MongoDB: {e}")
        return False


def validate_collection_for_query(collection_name: str, mongodb_uri: Optional[str] = None):
    """
    Validate that a collection can be used for RAG queries.
    
    Args:
        collection_name: Collection name in format "collection" or "database.collection"
        mongodb_uri: Optional MongoDB URI
        
    Returns:
        Tuple of (is_valid, error_message)
        is_valid: True if collection can be queried
        error_message: None if valid, error message if invalid
    """
    if is_raw_document_collection(collection_name):
        return False, (
            f"Collection '{collection_name}' is a raw document store and "
            "cannot be queried directly. Select the corresponding vector "
            "collection (e.g., 'srugenai_db.movies')."
        )
    
    if not has_vector_index(collection_name, mongodb_uri):
        # Parse collection name for better error message
        if '.' in collection_name:
            db_name, coll_name = collection_name.split('.', 1)
        else:
            db_name = Config.VECTOR_DATA_DATABASE_NAME or Config.MONGODB_DATABASE_NAME
            coll_name = collection_name
        
        error_msg = (
            f"Collection '{collection_name}' does not have a vector search index. "
            "Only vector collections with embeddings can be queried.\n\n"
            "To fix this:\n"
            f"1. Go to MongoDB Atlas: https://cloud.mongodb.com\n"
            f"2. Navigate to your cluster → Search tab\n"
            f"3. Create Search Index:\n"
            f"   - Index Name: default\n"
            f"   - Database: {db_name}\n"
            f"   - Collection: {coll_name}\n"
            f"   - Use JSON Editor with vector field configuration\n"
            f"4. See CREATE_VECTOR_INDEX_srugenai_db_movies.md for detailed steps\n\n"
            f"Or run: python setup_vector_index_for_collection.py {collection_name}"
        )
        return False, error_msg
    
    return True, None

