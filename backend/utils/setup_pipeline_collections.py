"""Script to set up collections and indexes for the two-stage RAG pipeline."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pymongo import MongoClient
from pymongo.errors import OperationFailure
from backend.config import Config


def setup_pipeline_collections():
    """Set up raw_documents and vector_data collections with proper indexes."""
    
    if not Config.MONGODB_URI:
        print("ERROR: MONGODB_URI not configured")
        return False
    
    try:
        # Connect to MongoDB
        connection_params = {
            'serverSelectionTimeoutMS': 30000,
            'connectTimeoutMS': 30000,
            'socketTimeoutMS': 30000,
        }
        
        if Config.MONGODB_URI.startswith('mongodb+srv://'):
            if 'retryWrites' not in Config.MONGODB_URI:
                separator = '&' if '?' in Config.MONGODB_URI else '?'
                uri_with_params = f"{Config.MONGODB_URI}{separator}retryWrites=true&w=majority"
            else:
                uri_with_params = Config.MONGODB_URI
        else:
            connection_params['tls'] = True
            connection_params['tlsAllowInvalidCertificates'] = False
            uri_with_params = Config.MONGODB_URI
        
        client = MongoClient(uri_with_params, **connection_params)
        client.admin.command('ping')
        
        print("=" * 70)
        print("Setting up Two-Stage RAG Pipeline Collections")
        print("=" * 70)
        
        # Setup raw_documents collection
        raw_db = client[Config.RAW_DOCUMENTS_DATABASE_NAME]
        raw_collection = raw_db[Config.RAW_DOCUMENTS_COLLECTION_NAME]
        
        print(f"\n[1/2] Setting up '{Config.RAW_DOCUMENTS_COLLECTION_NAME}' collection...")
        print(f"      Database: {Config.RAW_DOCUMENTS_DATABASE_NAME}")
        
        # Create indexes for raw_documents
        indexes_created = []
        try:
            raw_collection.create_index('origin_id', unique=False)
            indexes_created.append('origin_id')
        except Exception as e:
            print(f"      Warning: Could not create origin_id index: {e}")
        
        try:
            raw_collection.create_index('status')
            indexes_created.append('status')
        except Exception as e:
            print(f"      Warning: Could not create status index: {e}")
        
        try:
            raw_collection.create_index([('origin_source_type', 1), ('origin_source_id', 1)])
            indexes_created.append('origin_source_type + origin_source_id')
        except Exception as e:
            print(f"      Warning: Could not create origin_source index: {e}")
        
        try:
            raw_collection.create_index('created_at')
            indexes_created.append('created_at')
        except Exception as e:
            print(f"      Warning: Could not create created_at index: {e}")
        
        print(f"      ✓ Created indexes: {', '.join(indexes_created)}")
        
        # Setup vector_data collection
        vector_db = client[Config.VECTOR_DATA_DATABASE_NAME]
        vector_collection = vector_db[Config.VECTOR_DATA_COLLECTION_NAME]
        
        print(f"\n[2/2] Setting up '{Config.VECTOR_DATA_COLLECTION_NAME}' collection...")
        print(f"      Database: {Config.VECTOR_DATA_DATABASE_NAME}")
        
        # Create standard indexes
        vector_indexes_created = []
        try:
            vector_collection.create_index('raw_document_id')
            vector_indexes_created.append('raw_document_id')
        except Exception as e:
            print(f"      Warning: Could not create raw_document_id index: {e}")
        
        try:
            vector_collection.create_index('origin_id')
            vector_indexes_created.append('origin_id')
        except Exception as e:
            print(f"      Warning: Could not create origin_id index: {e}")
        
        try:
            vector_collection.create_index('document_id')
            vector_indexes_created.append('document_id')
        except Exception as e:
            print(f"      Warning: Could not create document_id index: {e}")
        
        print(f"      ✓ Created indexes: {', '.join(vector_indexes_created)}")
        
        # Note about vector search index
        print(f"\n⚠️  IMPORTANT: Vector Search Index Setup")
        print(f"   The vector search index '{Config.VECTOR_DATA_INDEX_NAME}' must be created")
        print(f"   manually in MongoDB Atlas UI or via Atlas API.")
        print(f"   Required configuration:")
        print(f"   - Index Name: {Config.VECTOR_DATA_INDEX_NAME}")
        print(f"   - Collection: {Config.VECTOR_DATA_COLLECTION_NAME}")
        print(f"   - Database: {Config.VECTOR_DATA_DATABASE_NAME}")
        print(f"   - Field: embedding")
        print(f"   - Dimensions: 384 (for all-MiniLM-L6-v2)")
        print(f"   - Similarity: cosine")
        
        print("\n" + "=" * 70)
        print("✓ Collection setup complete!")
        print("=" * 70)
        
        client.close()
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR setting up collections: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = setup_pipeline_collections()
    sys.exit(0 if success else 1)

