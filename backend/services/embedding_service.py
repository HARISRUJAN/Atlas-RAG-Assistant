"""Embedding generation service using sentence-transformers."""

from typing import List
from sentence_transformers import SentenceTransformer
from backend.config import Config


class EmbeddingService:
    """Service for generating text embeddings using local models."""
    
    def __init__(self):
        """Initialize embedding service with sentence-transformers."""
        self.model_name = Config.EMBEDDING_MODEL
        print(f"Loading embedding model: {self.model_name}...")
        self.model = SentenceTransformer(self.model_name)
        print(f"Embedding model loaded. Dimension: {self.get_embedding_dimension()}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text
            
        Returns:
            List of embedding values
        """
        embedding = self.model.encode(text, convert_to_tensor=False)
        return embedding.tolist()
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        embeddings = self.model.encode(texts, convert_to_tensor=False)
        return [emb.tolist() for emb in embeddings]
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings for this model."""
        # Common sentence-transformer models and their dimensions
        dimension_map = {
            'all-MiniLM-L6-v2': 384,
            'all-mpnet-base-v2': 768,
            'all-MiniLM-L12-v2': 384,
            'paraphrase-MiniLM-L6-v2': 384,
            'paraphrase-mpnet-base-v2': 768,
        }
        
        # Check if model name is in map
        if self.model_name in dimension_map:
            return dimension_map[self.model_name]
        
        # Otherwise, get dimension from model
        return self.model.get_sentence_embedding_dimension()

