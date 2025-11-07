"""MongoDB Vector Store service for storing and retrieving document chunks."""

from typing import List, Dict, Any
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from backend.config import Config
from backend.models.document import DocumentChunk


class VectorStoreService:
    """Service for MongoDB Vector Store operations."""
    
    def __init__(self):
        """Initialize vector store service."""
        self.client = MongoClient(Config.MONGODB_URI)
        self.db = self.client[Config.MONGODB_DATABASE_NAME]
        self.collection = self.db[Config.MONGODB_COLLECTION_NAME]
        self.index_name = Config.MONGODB_VECTOR_INDEX_NAME
    
    def test_connection(self) -> bool:
        """Test MongoDB connection."""
        try:
            self.client.admin.command('ping')
            return True
        except ConnectionFailure:
            return False
    
    def store_chunks(self, chunks: List[DocumentChunk]) -> int:
        """
        Store document chunks in MongoDB.
        
        Args:
            chunks: List of document chunks with embeddings
            
        Returns:
            Number of chunks stored
        """
        if not chunks:
            return 0
        
        documents = [chunk.to_dict() for chunk in chunks]
        result = self.collection.insert_many(documents)
        return len(result.inserted_ids)
    
    def vector_search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            
        Returns:
            List of matching documents with scores
        """
        try:
            # MongoDB Atlas Vector Search aggregation pipeline
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": self.index_name,
                        "path": "embedding",
                        "queryVector": query_embedding,
                        "numCandidates": top_k * 10,
                        "limit": top_k
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "chunk_id": 1,
                        "document_id": 1,
                        "file_name": 1,
                        "chunk_index": 1,
                        "content": 1,
                        "line_start": 1,
                        "line_end": 1,
                        "metadata": 1,
                        "score": {"$meta": "vectorSearchScore"}
                    }
                }
            ]
            
            results = list(self.collection.aggregate(pipeline))
            return results
            
        except OperationFailure as e:
            # If vector search index doesn't exist, fallback to basic search
            print(f"Vector search failed: {e}")
            print("Note: Make sure to create the vector search index in MongoDB Atlas")
            return []
    
    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get all chunks for a specific document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            List of document chunks
        """
        return list(self.collection.find(
            {"document_id": document_id},
            {"_id": 0}
        ).sort("chunk_index", 1))
    
    def delete_document(self, document_id: str) -> int:
        """
        Delete all chunks for a document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Number of chunks deleted
        """
        result = self.collection.delete_many({"document_id": document_id})
        return result.deleted_count
    
    def get_all_documents(self) -> List[Dict[str, Any]]:
        """
        Get list of all documents (unique document IDs with metadata).
        
        Returns:
            List of document metadata
        """
        pipeline = [
            {
                "$group": {
                    "_id": "$document_id",
                    "file_name": {"$first": "$file_name"},
                    "chunk_count": {"$sum": 1}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "document_id": "$_id",
                    "file_name": 1,
                    "chunk_count": 1
                }
            }
        ]
        return list(self.collection.aggregate(pipeline))
    
    def close(self):
        """Close MongoDB connection."""
        self.client.close()

