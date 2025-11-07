"""Configuration management for the RAG application."""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration class."""
    
    # MongoDB Configuration
    MONGODB_URI = os.getenv('MONGODB_URI')
    MONGODB_DATABASE_NAME = os.getenv('MONGODB_DATABASE_NAME', 'rag_database')
    MONGODB_COLLECTION_NAME = os.getenv('MONGODB_COLLECTION_NAME', 'documents')
    MONGODB_VECTOR_INDEX_NAME = os.getenv('MONGODB_VECTOR_INDEX_NAME', 'vector_index')
    
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
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
    
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
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        return True


# Create upload folder if it doesn't exist
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

