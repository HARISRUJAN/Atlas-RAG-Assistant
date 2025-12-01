"""Utility script to create vector indexes on semantic collections.

This script should be run once to set up vector search indexes on semantic collections.
Vector indexes must be created via MongoDB Atlas UI or this script.

Usage:
    python -m backend.utils.setup_semantic_indexes
    python -m backend.utils.setup_semantic_indexes --collection collection_data --database srugenai_db
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.config import Config
from backend.services.raw_document_store import RawDocumentStore


def create_semantic_indexes(
    origin_collection_name: str,
    origin_db_name: Optional[str] = None,
    mongodb_uri: Optional[str] = None
):
    """
    Create indexes on a semantic collection.
    
    Note: Vector indexes must be created via MongoDB Atlas UI.
    This script creates regular indexes (origin_id, chunk_id, etc.).
    
    Args:
        origin_collection_name: Name of the origin collection
        origin_db_name: Name of the origin database
        mongodb_uri: MongoDB URI
    """
    try:
        print(f"\n{'='*70}")
        print(f"Setting up indexes for semantic collection")
        print(f"{'='*70}")
        print(f"Origin collection: {origin_collection_name}")
        
        semantic_collection_name = Config.get_semantic_collection_name(origin_collection_name)
        print(f"Semantic collection: {semantic_collection_name}")
        
        # Create RawDocumentStore to access semantic collection
        raw_store = RawDocumentStore(mongodb_uri=mongodb_uri)
        
        # Get semantic collection (this will create indexes)
        semantic_collection = raw_store.get_semantic_collection(
            origin_collection_name=origin_collection_name,
            origin_db_name=origin_db_name
        )
        
        print(f"\n✓ Regular indexes created on semantic collection")
        print(f"\n⚠️  IMPORTANT: Vector index must be created via MongoDB Atlas UI")
        print(f"\nTo create vector index:")
        print(f"1. Go to MongoDB Atlas: https://cloud.mongodb.com")
        print(f"2. Navigate to your cluster → Search tab")
        print(f"3. Create Search Index:")
        print(f"   - Index Name: default (or vector_index)")
        print(f"   - Database: {origin_db_name or Config.ORIGIN_DB_NAME}")
        print(f"   - Collection: {semantic_collection_name}")
        print(f"   - Use JSON Editor with this configuration:")
        print(f"""
{{
  "fields": [
    {{
      "type": "vector",
      "path": "embedding",
      "numDimensions": 384,
      "similarity": "cosine"
    }}
  ]
}}
        """)
        
        raw_store.close()
        print(f"\n{'='*70}\n")
        
    except Exception as e:
        print(f"\n❌ Error setting up indexes: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Setup indexes for semantic collections')
    parser.add_argument(
        '--collection',
        type=str,
        default=Config.ORIGIN_COLLECTION_NAME,
        help=f'Origin collection name (default: {Config.ORIGIN_COLLECTION_NAME})'
    )
    parser.add_argument(
        '--database',
        type=str,
        default=Config.ORIGIN_DB_NAME,
        help=f'Origin database name (default: {Config.ORIGIN_DB_NAME})'
    )
    parser.add_argument(
        '--uri',
        type=str,
        default=Config.MONGODB_URI,
        help='MongoDB URI (default: from Config.MONGODB_URI)'
    )
    
    args = parser.parse_args()
    
    if not args.uri:
        print("❌ Error: MongoDB URI is required. Provide --uri or set MONGODB_URI in .env")
        sys.exit(1)
    
    create_semantic_indexes(
        origin_collection_name=args.collection,
        origin_db_name=args.database,
        mongodb_uri=args.uri
    )


if __name__ == '__main__':
    from typing import Optional
    main()

