"""Configuration management for the RAG application."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
# Try to load from project root first, then current directory

# Get project root (parent of backend directory if we're in backend)
project_root = Path(__file__).parent.parent
env_path = project_root / '.env'

# Load .env file
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"[Config] Loaded .env from: {env_path}")
else:
    # Fallback to current directory
    load_dotenv()
    print(f"[Config] Loaded .env from current directory")


class Config:
    """Application configuration class."""
    
    # MongoDB Configuration
    MONGODB_URI = os.getenv('MONGODB_URI')
    MONGODB_DATABASE_NAME = os.getenv('MONGODB_DATABASE_NAME', 'rag_database')
    MONGODB_COLLECTION_NAME = os.getenv('MONGODB_COLLECTION_NAME', 'documents')
    MONGODB_VECTOR_INDEX_NAME = os.getenv('MONGODB_VECTOR_INDEX_NAME', 'vector_index')
    
    # Two-Stage Pipeline Configuration
    RAW_DOCUMENTS_DATABASE_NAME = os.getenv('RAW_DOCUMENTS_DATABASE_NAME', MONGODB_DATABASE_NAME)
    RAW_DOCUMENTS_COLLECTION_NAME = os.getenv('RAW_DOCUMENTS_COLLECTION_NAME', 'raw_documents')
    VECTOR_DATA_DATABASE_NAME = os.getenv('VECTOR_DATA_DATABASE_NAME', MONGODB_DATABASE_NAME)
    VECTOR_DATA_COLLECTION_NAME = os.getenv('VECTOR_DATA_COLLECTION_NAME', 'vector_data')
    VECTOR_DATA_INDEX_NAME = os.getenv('VECTOR_DATA_INDEX_NAME', 'vector_index')
    
    # LLM Configuration
    LLM_API_URL = os.getenv('LLM_API_URL')
    LLM_API_KEY = os.getenv('LLM_API_KEY')
    LLM_MODEL = os.getenv('LLM_MODEL', 'llama3.2:latest')
    
    # Embedding Configuration (using local sentence-transformers)
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
    
    # Chunking Configuration
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 1000))
    CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', 200))
    
    # File Upload Configuration
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', 10))
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
    ALLOWED_EXTENSIONS = set(os.getenv('ALLOWED_EXTENSIONS', 'pdf,txt,docx,md').split(','))
    UPLOAD_FOLDER = 'uploads'
    
    # Flask Configuration
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5002))
    
    @staticmethod
    def validate():
        """Validate required configuration."""
        required_vars = [
            ('MONGODB_URI', Config.MONGODB_URI),
            ('LLM_API_URL', Config.LLM_API_URL),
            ('LLM_API_KEY', Config.LLM_API_KEY),
        ]
        
        missing = [var_name for var_name, var_value in required_vars if not var_value]
        
        if missing:
            print(f"[Config] WARNING: Missing required environment variables: {', '.join(missing)}")
            print(f"[Config] MONGODB_URI present: {bool(Config.MONGODB_URI)}")
            print(f"[Config] LLM_API_URL present: {bool(Config.LLM_API_URL)}")
            print(f"[Config] LLM_API_KEY present: {bool(Config.LLM_API_KEY)}")
            # Don't exit - let the app start and show errors when features are used
            # raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        return True


# Create upload folder if it doesn't exist
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

