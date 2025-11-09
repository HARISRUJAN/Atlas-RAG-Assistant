"""RAG service for orchestrating retrieval and generation."""

import requests
from typing import List
from backend.config import Config
from backend.models.query import QueryRequest, QueryResponse, SourceReference
from backend.services.embedding_service import EmbeddingService
from backend.services.vector_store import VectorStoreService


class RAGService:
    """Service for Retrieval-Augmented Generation."""
    
    def __init__(self, collection_name: str = None, database_name: str = None, index_name: str = None):
        """
        Initialize RAG service.
        
        Args:
            collection_name: Optional collection name. Can be "collection" or "database.collection" format.
                            Defaults to Config.MONGODB_COLLECTION_NAME
            database_name: Optional database name. If collection_name contains ".", this is ignored.
                          Defaults to Config.MONGODB_DATABASE_NAME
            index_name: Optional index name. Defaults to Config.MONGODB_VECTOR_INDEX_NAME
        """
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStoreService(
            collection_name=collection_name, 
            database_name=database_name,
            index_name=index_name
        )
        self.llm_api_url = Config.LLM_API_URL
        self.llm_api_key = Config.LLM_API_KEY
        self.llm_model = Config.LLM_MODEL
    
    def query(self, request: QueryRequest) -> QueryResponse:
        """
        Process a query through the RAG pipeline.
        
        Args:
            request: Query request
            
        Returns:
            Query response with answer and sources
        """
        # Step 1: Generate embedding for the query
        query_embedding = self.embedding_service.generate_embedding(request.query)
        
        # Step 2: Retrieve relevant chunks from vector store
        search_results = self.vector_store.vector_search(
            query_embedding=query_embedding,
            top_k=request.top_k
        )
        
        if not search_results:
            return QueryResponse(
                answer="I don't have enough information to answer this question. Please upload relevant documents first.",
                sources=[],
                query=request.query
            )
        
        # Step 3: Format context from retrieved chunks
        context = self._format_context(search_results)
        
        # Step 4: Generate answer using LLM
        answer = self._generate_answer(request.query, context)
        
        # Step 5: Create source references
        sources = self._create_source_references(search_results)
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            query=request.query
        )
    
    def _format_context(self, search_results: List[dict]) -> str:
        """
        Format search results into context string.
        
        Args:
            search_results: List of search results
            
        Returns:
            Formatted context string
        """
        context_parts = []
        for idx, result in enumerate(search_results, 1):
            file_name = result.get('file_name', 'Unknown')
            line_start = result.get('line_start', 0)
            line_end = result.get('line_end', 0)
            content = result.get('content', '')
            
            context_parts.append(
                f"[Source {idx}: {file_name}, lines {line_start}-{line_end}]\n{content}\n"
            )
        
        return "\n".join(context_parts)
    
    def _generate_answer(self, query: str, context: str) -> str:
        """
        Generate answer using LLM.
        
        Args:
            query: User query
            context: Context from retrieved documents
            
        Returns:
            Generated answer
        """
        # Create prompt
        prompt = self._create_prompt(query, context)
        
        try:
            # Call Llama 3.2 API (Ollama format)
            response = requests.post(
                self.llm_api_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.llm_api_key}"
                },
                json={
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                    "max_tokens": 500
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                # Extract answer from response
                answer = result.get('response', result.get('choices', [{}])[0].get('text', ''))
                return answer.strip()
            else:
                return f"Error generating answer: {response.status_code} - {response.text}"
                
        except requests.exceptions.RequestException as e:
            return f"Error connecting to LLM: {str(e)}"
    
    def _create_prompt(self, query: str, context: str) -> str:
        """
        Create prompt for LLM.
        
        Args:
            query: User query
            context: Retrieved context
            
        Returns:
            Formatted prompt
        """
        prompt = f"""You are a helpful AI assistant. Answer the question based on the provided context. 
If you cannot answer based on the context, say so clearly.

Context:
{context}

Question: {query}

Answer: Provide a clear, concise answer based on the context above. If you reference information from the context, be specific about which source it comes from."""
        
        return prompt
    
    def _create_source_references(self, search_results: List[dict]) -> List[SourceReference]:
        """
        Create source references from search results.
        
        Args:
            search_results: List of search results
            
        Returns:
            List of source references
        """
        sources = []
        for result in search_results:
            source = SourceReference(
                file_name=result.get('file_name', 'Unknown'),
                line_start=result.get('line_start', 0),
                line_end=result.get('line_end', 0),
                content=result.get('content', '')[:200] + "...",  # Truncate for preview
                relevance_score=result.get('score', 0.0)
            )
            sources.append(source)
        
        return sources

