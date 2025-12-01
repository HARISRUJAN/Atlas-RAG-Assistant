"""Quick script to check if vector search index exists and is working."""

import sys
import io
import os
from pathlib import Path

# Set UTF-8 encoding for stdout/stderr on Windows
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    if not hasattr(sys.stdout, 'reconfigure'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if not hasattr(sys.stderr, 'reconfigure'):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from pymongo import MongoClient
from backend.config import Config

def check_vector_index(collection_path: str):
    """Check if vector search index exists and is working."""
    # Parse collection path
    if '.' in collection_path:
        parts = collection_path.split('.', 1)
        db_name = parts[0]
        coll_name = parts[1]
    else:
        print("Error: Collection path must be in 'database.collection' format")
        return
    
    # Get MongoDB URI
    mongodb_uri = Config.MONGODB_URI
    if not mongodb_uri:
        print("Error: MONGODB_URI not configured in .env file")
        return
    
    print(f"\n{'='*70}")
    print(f"Checking Vector Search Index Status")
    print(f"{'='*70}")
    print(f"Collection: {collection_path}")
    print(f"Database: {db_name}")
    print(f"Collection Name: {coll_name}\n")
    
    try:
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=10000)
        db = client[db_name]
        collection = db[coll_name]
        
        # Check document count
        doc_count = collection.count_documents({})
        print(f"✓ Collection has {doc_count} documents")
        
        # Check for embeddings
        doc_with_embedding = collection.count_documents({"embedding": {"$exists": True}})
        print(f"✓ Documents with embeddings: {doc_with_embedding}")
        
        if doc_with_embedding == 0:
            print("\n❌ ERROR: No documents have embeddings!")
            print("   Please re-ingest your documents to generate embeddings.")
            client.close()
            return
        
        # Get sample document to check embedding dimensions
        sample_doc = collection.find_one({"embedding": {"$exists": True}})
        if sample_doc and 'embedding' in sample_doc:
            emb = sample_doc['embedding']
            if isinstance(emb, list):
                print(f"✓ Embedding dimensions: {len(emb)} (expected: 384)")
                if len(emb) != 384:
                    print(f"  ⚠️  WARNING: Embedding dimensions don't match expected 384!")
            else:
                print(f"❌ ERROR: Embedding is not a list: {type(emb)}")
                client.close()
                return
        
        # Test vector search with different index names
        print(f"\nTesting vector search indexes...")
        index_names_to_try = ['default', 'vector_index', 'vector_data_index', 'vectorIndex']
        working_index = None
        
        for index_name in index_names_to_try:
            try:
                test_pipeline = [
                    {
                        "$vectorSearch": {
                            "index": index_name,
                            "path": "embedding",
                            "queryVector": emb[:384] if isinstance(emb, list) and len(emb) >= 384 else emb,
                            "numCandidates": 1,
                            "limit": 1
                        }
                    },
                    {"$limit": 1}
                ]
                results = list(collection.aggregate(test_pipeline))
                if results:
                    print(f"  ✓ Index '{index_name}' is WORKING!")
                    working_index = index_name
                    break
            except Exception as e:
                error_msg = str(e).lower()
                if 'index' in error_msg or 'not found' in error_msg:
                    print(f"  ✗ Index '{index_name}' not found")
                else:
                    print(f"  ✗ Index '{index_name}' error: {str(e)[:100]}")
        
        print(f"\n{'='*70}")
        if working_index:
            print(f"✓ SUCCESS: Vector search index '{working_index}' is working!")
            print(f"  You can now run queries on this collection.")
        else:
            print(f"❌ ERROR: No working vector search index found!")
            print(f"\nTo fix this:")
            print(f"1. Go to MongoDB Atlas: https://cloud.mongodb.com")
            print(f"2. Navigate to your cluster → Search tab")
            print(f"3. Create Search Index with name 'default' or 'vector_index'")
            print(f"4. Use JSON Editor with this config:")
            print(f'   {{"fields": [{{"type": "vector", "path": "embedding", "numDimensions": 384, "similarity": "cosine"}}]}}')
            print(f"5. Wait for index status to become 'Active'")
        print(f"{'='*70}\n")
        
        client.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python check_vector_index.py database.collection")
        print("Example: python check_vector_index.py sample_mflix.movies_semantic")
        sys.exit(1)
    
    check_vector_index(sys.argv[1])

