"""Helper script to set up vector search index for a semantic collection.

This script provides instructions and can parse collection paths in "database.collection" format.

Usage:
    python setup_vector_index_for_collection.py rag_database.connections_semantic
    python setup_vector_index_for_collection.py rag_database.connections_semantic --uri "mongodb+srv://..."
"""

import sys
import io

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

import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.config import Config
from backend.services.raw_document_store import RawDocumentStore
from typing import Optional


def setup_vector_index_instructions(collection_path: str, mongodb_uri: Optional[str] = None):
    """
    Provide instructions for creating a vector search index.
    
    Args:
        collection_path: Full collection path in "database.collection" format
        mongodb_uri: Optional MongoDB URI
    """
    # Parse collection path
    if '.' in collection_path:
        parts = collection_path.split('.', 1)
        if len(parts) == 2:
            db_name, coll_name = parts
        else:
            print(f"❌ Error: Invalid collection path format: {collection_path}")
            print("Expected format: database.collection (e.g., rag_database.connections_semantic)")
            sys.exit(1)
    else:
        print(f"❌ Error: Collection path must include database name")
        print("Expected format: database.collection (e.g., rag_database.connections_semantic)")
        sys.exit(1)
    
    print(f"\n{'='*70}")
    print(f"Vector Search Index Setup Instructions")
    print(f"{'='*70}")
    print(f"Collection: {collection_path}")
    print(f"Database: {db_name}")
    print(f"Collection Name: {coll_name}")
    print(f"\n⚠️  IMPORTANT: Vector indexes must be created via MongoDB Atlas UI")
    print(f"\nTo create vector index:")
    print(f"1. Go to MongoDB Atlas: https://cloud.mongodb.com")
    print(f"2. Navigate to your cluster → Search tab")
    print(f"3. Click 'Create Search Index'")
    print(f"4. Select 'JSON Editor'")
    print(f"5. Use this configuration:")
    print(f"\n{{")
    print(f'  "fields": [')
    print(f'    {{')
    print(f'      "type": "vector",')
    print(f'      "path": "embedding",')
    print(f'      "numDimensions": 384,')
    print(f'      "similarity": "cosine"')
    print(f'    }}')
    print(f'  ]')
    print(f"}}\n")
    print(f"6. Set Index Name: default (or vector_index)")
    print(f"7. Select Database: {db_name}")
    print(f"8. Select Collection: {coll_name}")
    print(f"9. Click 'Create Search Index'")
    print(f"\n{'='*70}\n")
    
    # Also create regular indexes if MongoDB URI is provided
    if mongodb_uri:
        try:
            print("Creating regular indexes on semantic collection...")
            raw_store = RawDocumentStore(mongodb_uri=mongodb_uri)
            
            # Get semantic collection (this will create regular indexes)
            semantic_collection = raw_store.get_semantic_collection(
                origin_collection_name=coll_name.replace('_semantic', '') if coll_name.endswith('_semantic') else coll_name,
                origin_db_name=db_name
            )
            
            print("✓ Regular indexes created (origin_id, chunk_id, etc.)")
            print("⚠️  Remember: Vector search index must still be created via Atlas UI")
            
            raw_store.close()
        except Exception as e:
            print(f"⚠️  Warning: Could not create regular indexes: {e}")
            print("You can still create the vector index manually via Atlas UI")


def main():
    parser = argparse.ArgumentParser(
        description='Setup instructions for vector search index on a semantic collection'
    )
    parser.add_argument(
        'collection',
        type=str,
        help='Collection path in "database.collection" format (e.g., rag_database.connections_semantic)'
    )
    parser.add_argument(
        '--uri',
        type=str,
        default=Config.MONGODB_URI,
        help='MongoDB URI (default: from Config.MONGODB_URI)'
    )
    
    args = parser.parse_args()
    
    if not args.collection:
        print("❌ Error: Collection path is required")
        print("Usage: python setup_vector_index_for_collection.py database.collection")
        sys.exit(1)
    
    setup_vector_index_instructions(args.collection, args.uri)


if __name__ == '__main__':
    main()

