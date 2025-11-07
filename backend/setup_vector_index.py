"""Script to create MongoDB Atlas Vector Search Index."""

import json
from pymongo import MongoClient
from backend.config import Config


def create_vector_search_index():
    """Create vector search index in MongoDB Atlas."""
    
    print("Connecting to MongoDB Atlas...")
    client = MongoClient(Config.MONGODB_URI)
    db = client[Config.MONGODB_DATABASE_NAME]
    collection = db[Config.MONGODB_COLLECTION_NAME]
    
    # Test connection
    try:
        client.admin.command('ping')
        print("✓ Successfully connected to MongoDB Atlas")
    except Exception as e:
        print(f"✗ Failed to connect to MongoDB: {e}")
        return False
    
    # Vector search index definition
    index_definition = {
        "name": Config.MONGODB_VECTOR_INDEX_NAME,
        "type": "vectorSearch",
        "definition": {
            "fields": [
                {
                    "type": "vector",
                    "path": "embedding",
                    "numDimensions": 384,  # For all-MiniLM-L6-v2
                    "similarity": "cosine"
                },
                {
                    "type": "filter",
                    "path": "document_id"
                },
                {
                    "type": "filter",
                    "path": "file_name"
                }
            ]
        }
    }
    
    print("\nVector Search Index Configuration:")
    print(json.dumps(index_definition, indent=2))
    
    print("\n" + "="*70)
    print("MANUAL INDEX CREATION REQUIRED")
    print("="*70)
    print("\nMongoDB Atlas Vector Search indexes must be created through the Atlas UI.")
    print("\nPlease follow these steps:")
    print("\n1. Go to your MongoDB Atlas dashboard")
    print("2. Navigate to your cluster")
    print("3. Click on 'Search' tab")
    print("4. Click 'Create Search Index'")
    print("5. Select 'JSON Editor'")
    print("6. Use the following configuration:")
    print("\n" + "-"*70)
    
    atlas_config = {
        "mappings": {
            "dynamic": True,
            "fields": {
                "embedding": {
                    "type": "knnVector",
                    "dimensions": 384,
                    "similarity": "cosine"
                }
            }
        }
    }
    
    print(json.dumps(atlas_config, indent=2))
    print("-"*70)
    
    print(f"\n7. Name the index: {Config.MONGODB_VECTOR_INDEX_NAME}")
    print(f"8. Select database: {Config.MONGODB_DATABASE_NAME}")
    print(f"9. Select collection: {Config.MONGODB_COLLECTION_NAME}")
    print("10. Click 'Create Search Index'")
    
    print("\n" + "="*70)
    print("Collection Info:")
    print(f"  Database: {Config.MONGODB_DATABASE_NAME}")
    print(f"  Collection: {Config.MONGODB_COLLECTION_NAME}")
    print(f"  Index Name: {Config.MONGODB_VECTOR_INDEX_NAME}")
    print("="*70)
    
    # Check if collection exists and has documents
    doc_count = collection.count_documents({})
    print(f"\nCurrent documents in collection: {doc_count}")
    
    client.close()
    return True


if __name__ == '__main__':
    Config.validate()
    create_vector_search_index()

