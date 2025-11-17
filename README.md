# MongoDB Atlas RAG System

A production-grade **Retrieval-Augmented Generation (RAG)** system demonstrating advanced LangChain integration with MongoDB Atlas Vector Search and Llama 3.2.

![MongoDB RAG System Demo](demo.png)

## 🎯 Project Overview

This system implements a complete RAG pipeline that:
- Processes and chunks documents with line number preservation
- Generates embeddings using local sentence-transformers models
- Stores vectors in MongoDB Atlas with semantic search capabilities
- Retrieves contextually relevant chunks using vector similarity
- Generates accurate, source-cited answers using Llama 3.2
- **NEW**: Supports multiple MongoDB databases and collections
- **NEW**: Dynamic question generation based on collection content
- **NEW**: Hierarchical collection browser with tree view
- **NEW**: Three-column UI layout for improved user experience

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend Layer                        │
│  React + TypeScript + Tailwind CSS                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Collections  │  │ Chat         │  │ Upload/      │      │
│  │ Sidebar      │  │ Interface    │  │ Match Panel  │      │
│  │ • Database   │  │ • Query      │  │ • File       │      │
│  │   Tree View  │  │   Input      │  │   Upload     │      │
│  │ • Collection │  │ • Dynamic    │  │ • Source     │      │
│  │   Selection  │  │   Questions  │  │   Matches    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────┬──────────────────────────────────────┘
                        │ HTTP/REST API
┌───────────────────────▼──────────────────────────────────────┐
│                      Backend Layer                            │
│  Flask + LangChain + MongoDB                                 │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Document   │  │  Embedding  │  │   Vector     │       │
│  │  Processor   │──│   Service   │──│    Store     │       │
│  └──────────────┘  └──────────────┘  └──────┬───────┘       │
│                                              │                │
│  ┌──────────────┐  ┌──────────────────────────────────────┐ │
│  │ Collections  │  │           RAG Service (LangChain)     │ │
│  │  Service     │  │  • Vector Retriever                  │ │
│  │  • List DBs  │  │  • Context Assembly                  │ │
│  │  • List      │  │  • LLM Chain (Llama 3.2)            │ │
│  │    Collections│  │  • Response Formatting              │ │
│  │  • Generate  │  │  • Multi-Collection Support          │ │
│  │    Questions │  └──────────────────────────────────────┘ │
│  └──────────────┘                                            │
└───────────────────────┬──────────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────────┐
│                  MongoDB Atlas                                 │
│  • Vector Search Index (384 dimensions)                       │
│  • Cosine Similarity                                           │
│  • Document Chunks with Metadata                               │
└────────────────────────────────────────────────────────────────┘
```

## 🔗 RAG Chain Implementation

### Core RAG Pipeline

The RAG chain is implemented in `backend/services/rag_service.py` using LangChain's modular architecture:

```python
# 1. Document Processing & Chunking
Document → Text Extraction → RecursiveCharacterTextSplitter → Chunks with Line Numbers

# 2. Embedding Generation
Chunks → SentenceTransformer (all-MiniLM-L6-v2) → 384-dimensional vectors

# 3. Vector Storage
Vectors + Metadata → MongoDB Atlas Vector Store → Indexed for Search

# 4. Retrieval Phase
User Query → Query Embedding → Vector Search → Top-K Relevant Chunks

# 5. Generation Phase
Retrieved Chunks + Query → Context Assembly → LLM Prompt → Generated Answer
```

### LangChain Components Used

#### 1. **Document Loaders** (`langchain_community.document_loaders`)
- **PyPDFLoader**: PDF text extraction
- **TextLoader**: Plain text files
- **Docx2txtLoader**: Microsoft Word documents
- **UnstructuredMarkdownLoader**: Markdown files

#### 2. **Text Splitters** (`langchain_text_splitters`)
- **RecursiveCharacterTextSplitter**: Intelligent chunking with overlap
  - Preserves document structure
  - Maintains line number tracking for citations
  - Configurable chunk size (1000) and overlap (200)

#### 3. **Vector Stores** (`langchain_community.vectorstores`)
- **MongoDBAtlasVectorSearch**: Native MongoDB integration
  - Custom embedding function wrapper
  - Vector search query construction
  - Metadata filtering capabilities

#### 4. **Retrievers** (`langchain.retrievers`)
- **VectorStoreRetriever**: Semantic similarity retrieval
  - Top-K retrieval (configurable)
  - Score-based ranking
  - Metadata preservation

#### 5. **LLM Integration** (`langchain.llms`)
- **Custom LLM Wrapper**: Llama 3.2 API integration
  - OpenAI-compatible endpoint support
  - Streaming capability
  - Token management

#### 6. **Chains** (`langchain.chains`)
- **RetrievalQA Chain**: End-to-end RAG pipeline
  - Automatic context injection
  - Prompt template management
  - Source attribution

### RAG Service Architecture

```python
class RAGService:
    """
    Orchestrates the complete RAG pipeline using LangChain components.
    """
    
    def __init__(self):
        # Initialize embedding service
        self.embedding_service = EmbeddingService()
        
        # Initialize vector store with MongoDB
        self.vector_store = MongoDBAtlasVectorSearch(
            embedding_function=self.embedding_service,
            collection=collection,
            index_name=index_name
        )
        
        # Create retriever
        self.retriever = self.vector_store.as_retriever(
            search_kwargs={"k": 5}  # Top 5 most relevant chunks
        )
        
        # Initialize LLM
        self.llm = CustomLlamaLLM(
            api_url=LLM_API_URL,
            api_key=LLM_API_KEY,
            model=LLM_MODEL
        )
        
        # Create RAG chain #############################################################################################
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.retriever,
            return_source_documents=True
        )
    
    def query(self, question: str) -> QueryResponse:
        """
        Execute RAG pipeline:
        1. Retrieve relevant chunks
        2. Assemble context
        3. Generate answer with LLM
        4. Format response with sources
        """
        result = self.qa_chain.invoke({"query": question})
        
        return {
            "answer": result["result"],
            "sources": self._format_sources(result["source_documents"]),
            "query": question
        }
```

## 📊 Data Flow

### Document Ingestion Flow

```
1. File Upload (PDF/TXT/DOCX/MD)
   ↓
2. Document Processor
   ├─→ Extract text content
   ├─→ Validate file type & size
   └─→ Return raw text
   ↓
3. Text Chunking (RecursiveCharacterTextSplitter)
   ├─→ Split into 1000-char chunks
   ├─→ 200-char overlap between chunks
   ├─→ Preserve line numbers (start, end)
   └─→ Return: [(chunk_text, line_start, line_end), ...]
   ↓
4. Embedding Generation (SentenceTransformer)
   ├─→ Model: all-MiniLM-L6-v2
   ├─→ Dimension: 384
   ├─→ Batch processing for efficiency
   └─→ Return: List[List[float]] (384-dim vectors)
   ↓
5. MongoDB Vector Store
   ├─→ Store chunks with embeddings
   ├─→ Metadata: file_name, line_start, line_end, content
   ├─→ Indexed for vector search
   └─→ Ready for retrieval
```

### Query Processing Flow

```
1. User Query Input
   ↓
2. Query Embedding
   ├─→ Generate 384-dim vector for query
   └─→ Same model as document embeddings
   ↓
3. Vector Search (MongoDB Atlas)
   ├─→ Cosine similarity search
   ├─→ Top-K retrieval (default: 5)
   ├─→ Score-based ranking
   └─→ Return: [(chunk, score, metadata), ...]
   ↓
4. Context Assembly
   ├─→ Combine top-K chunks
   ├─→ Add source metadata
   └─→ Format for LLM prompt
   ↓
5. LLM Generation (Llama 3.2)
   ├─→ Prompt: Query + Context + Instructions
   ├─→ Generate answer
   └─→ Return: Generated text
   ↓
6. Response Formatting
   ├─→ Combine answer + sources
   ├─→ Include file names & line numbers
   ├─→ Add relevance scores
   └─→ Return: QueryResponse
```

## 🔧 Technical Implementation Details

### Vector Search Configuration

**MongoDB Atlas Vector Search Index:**
```json
{
  "mappings": {
    "dynamic": true,
    "fields": {
      "embedding": {
        "type": "knnVector",
        "dimensions": 384,
        "similarity": "cosine"
      }
    }
  }
}
```

**Search Pipeline:**
```python
pipeline = [
    {
        "$vectorSearch": {
            "index": "vector_index",
            "path": "embedding",
            "queryVector": query_embedding,
            "numCandidates": 10,
            "limit": 5
        }
    },
    {
        "$project": {
            "file_name": 1,
            "content": 1,
            "line_start": 1,
            "line_end": 1,
            "score": {"$meta": "vectorSearchScore"}
        }
    }
]
```

### Chunking Strategy

- **Method**: RecursiveCharacterTextSplitter
- **Chunk Size**: 1000 characters
- **Overlap**: 200 characters
- **Separators**: `["\n\n", "\n", ". ", " ", ""]`
- **Line Tracking**: Custom implementation to preserve line numbers

### Embedding Model

- **Model**: `all-MiniLM-L6-v2` (sentence-transformers)
- **Dimensions**: 384
- **Similarity**: Cosine
- **Advantages**: 
  - Fast inference
  - Good semantic understanding
  - No API costs
  - Privacy-preserving (local)

### LLM Integration

- **Model**: Llama 3.2
- **API Format**: OpenAI-compatible
- **Prompt Template**:
  ```
  Context: {retrieved_chunks}
  
  Question: {user_query}
  
  Instructions:
  - Answer based only on the provided context
  - Cite sources with file names and line numbers
  - If context is insufficient, state so clearly
  ```

## 📁 Project Structure

```
mongo_rag/
├── backend/
│   ├── app.py                      # Flask application entry point
│   ├── config.py                   # Environment configuration
│   ├── models/                     # Data models
│   │   ├── document.py            # Document data structure
│   │   └── query.py                # Query request/response models
│   ├── services/                   # Core business logic
│   │   ├── document_processor.py  # Document loading & extraction
│   │   ├── embedding_service.py   # Embedding generation (sentence-transformers)
│   │   ├── vector_store.py        # MongoDB vector operations (multi-collection support)
│   │   └── rag_service.py         # RAG pipeline orchestration (LangChain)
│   ├── routes/                     # API endpoints
│   │   ├── upload.py               # File upload handler
│   │   ├── query.py               # Query processing endpoint
│   │   ├── collections.py         # Collections & questions endpoints (NEW)
│   │   └── health.py               # Health check endpoint
│   └── utils/                      # Utility functions
│       ├── file_validator.py       # File validation
│       ├── chunking.py             # Text chunking with line tracking
│       └── mongodb_client.py      # MongoDB connection utilities (NEW)
├── frontend/
│   ├── src/
│   │   ├── components/             # React components
│   │   │   ├── FileUpload.tsx     # Document upload UI
│   │   │   ├── QueryInput.tsx      # Query input with dynamic suggestions
│   │   │   ├── ResponseDisplay.tsx # Answer display
│   │   │   ├── CollectionSelector.tsx # Database/collection tree view (NEW)
│   │   │   └── SourceReference.tsx # Source citation component
│   │   ├── api.ts                  # API client (enhanced with collections API)
│   │   ├── types.ts                # TypeScript definitions (extended)
│   │   └── App.tsx                 # Main application component (3-column layout)
│   └── package.json               # Frontend dependencies
├── start_project.py                # Project startup script (NEW)
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB Atlas account
- Llama 3.2 API access

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/HARISRUJAN/Atlas-RAG-Assistant.git
cd Atlas-RAG-Assistant
```

2. **Backend Setup**
```bash
# Create virtual environment
python -m venv rag_env
rag_env\Scripts\activate  # Windows
source rag_env/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

3. **Frontend Setup**
```bash
cd frontend
npm install
```

4. **Environment Configuration**
Create `.env` file (⚠️ **NEVER commit this file to git**):
```env
# MongoDB Atlas Connection String
# Get this from MongoDB Atlas → Connect → Connect your application
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster-name>.<region>.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE_NAME=rag_database
MONGODB_COLLECTION_NAME=documents
MONGODB_VECTOR_INDEX_NAME=vector_index

# LLM API Configuration
LLM_API_URL=https://your-llama-api.com/v1/completions
LLM_API_KEY=your-api-key
LLM_MODEL=llama3.2:latest

# Embedding Configuration
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

**⚠️ Security Note:** Replace `<username>`, `<password>`, and `<cluster-name>` with your actual MongoDB Atlas credentials. Never commit the `.env` file to version control.

5. **Create MongoDB Vector Search Index**
- Go to MongoDB Atlas → Search → Create Index
- Database: `rag_database`, Collection: `documents`
- Use the JSON configuration shown in "Vector Search Configuration" above

6. **Run the Application**

**Option 1: Using the startup script (Recommended)**
```bash
# From project root
python start_project.py
```
This script will:
- Activate the virtual environment
- Start the Flask backend server
- Start the frontend development server
- Display connection information

**Option 2: Manual startup**
```bash
# Backend (from project root)
python -m backend.app

# Frontend (from frontend directory, in a new terminal)
cd frontend
npm run dev
```

Access the application at `http://localhost:5173`

## 🆕 New Features

### 1. Multi-Database & Collection Support

The system now supports querying across multiple MongoDB databases and collections:

- **Hierarchical View**: Browse all databases and their collections in a tree structure
- **Dynamic Selection**: Select any collection from your MongoDB Atlas instance
- **Flexible Querying**: Query specific collections without changing configuration
- **Collection Browser**: Left sidebar displays all available databases and collections

### 2. Dynamic Question Generation

Instead of hardcoded suggested questions, the system now generates context-aware questions:

- **Content-Based**: Questions are generated by analyzing actual documents in the selected collection
- **LLM-Powered**: Uses the same LLM to create relevant questions based on collection content
- **Automatic Updates**: Questions refresh when you select a different collection
- **Smart Sampling**: Analyzes sample documents to understand collection content

**API Endpoint**: `GET /api/collections/<database>/<collection>/questions`

### 3. Enhanced UI Layout

The interface has been redesigned with a three-column layout:

```
┌──────────────┬──────────────────────┬──────────────┐
│              │                      │              │
│ Collections  │    Chat Interface   │  Upload/     │
│ Sidebar      │                      │  Match       │
│              │  • Query Input       │  Panel       │
│ • Database   │  • Dynamic Questions │              │
│   Tree       │  • Response Display │  • File      │
│ • Collection │  • Source Citations │    Upload    │
│   Selection  │                      │  • Matched   │
│              │                      │    Sources   │
└──────────────┴──────────────────────┴──────────────┘
```

**Features:**
- **Left Panel**: Scrollable collection browser with expandable database/collection tree
- **Center Panel**: Full-height chat interface with query input and response display
- **Right Panel**: File upload and source match display
- **Responsive**: All panels are independently scrollable

### 4. Collection Management API

New backend endpoints for collection management:

- `GET /api/collections` - List all databases with their collections
- `GET /api/collections/<database>/<collection>/questions` - Generate dynamic questions for a collection

**Response Format:**
```json
{
  "databases": [
    {
      "name": "database_name",
      "collections": ["collection1", "collection2"]
    }
  ]
}
```

### 5. Enhanced Query API

The query endpoint now supports collection-specific queries:

**Request:**
```json
{
  "query": "What are the key details?",
  "collection_name": "database_name/collection_name"
}
```

**Benefits:**
- Query specific collections without reconfiguration
- Support for multiple vector indexes
- Isolated data queries per collection

## 🎓 Key LangChain Concepts Demonstrated

1. **Document Processing Pipeline**
   - Multi-format document loading
   - Intelligent text splitting
   - Metadata preservation

2. **Vector Store Integration**
   - Custom embedding function
   - MongoDB Atlas native support
   - Efficient similarity search

3. **Retrieval Strategies**
   - Top-K retrieval
   - Score-based ranking
   - Metadata filtering

4. **Chain Composition**
   - RetrievalQA chain
   - Context injection
   - Prompt templating

5. **LLM Abstraction**
   - Custom LLM wrapper
   - API compatibility layer
   - Streaming support

## 📈 Performance Optimizations

- **Batch Embedding**: Process multiple chunks simultaneously
- **Vector Index**: MongoDB Atlas optimized for similarity search
- **Chunk Overlap**: Prevents context loss at boundaries
- **Line Number Tracking**: Enables precise source citations
- **Top-K Retrieval**: Balances relevance and performance

## 🔒 Security Considerations

- **Environment variables** for sensitive data (`.env` file is gitignored)
- **Never commit** `.env` file or any files containing credentials
- File type validation
- Size limits (10MB max)
- No API keys or connection strings in codebase
- Local embedding generation (privacy-preserving)
- **MongoDB Connection Security**: 
  - SSL/TLS encryption for all connections
  - IP whitelisting support in MongoDB Atlas
  - Connection string validation
  - Automatic retry logic with proper error handling

**⚠️ If you've accidentally committed credentials:**
1. Rotate/change your MongoDB Atlas password immediately
2. Revoke the old database user in MongoDB Atlas
3. Check security logs for unauthorized access
4. Remove credentials from git history (use `git filter-branch` or BFG Repo-Cleaner)

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend Framework** | Flask (Python) |
| **RAG Framework** | LangChain |
| **Vector Database** | MongoDB Atlas Vector Search |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) |
| **LLM** | Llama 3.2 |
| **Frontend** | React + TypeScript + Vite |
| **Styling** | Tailwind CSS |
| **Document Processing** | PyPDF2, python-docx, markdown |

## 🐛 Troubleshooting

### MongoDB Connection Issues

If you encounter SSL/TLS connection errors:

1. **Check IP Whitelist**: 
   - Go to MongoDB Atlas → Network Access
   - Add your current IP address or `0.0.0.0/0` (for testing only)
   - Wait 1-2 minutes for changes to propagate

2. **Verify Connection String**:
   - Ensure format: `mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority`
   - Check username and password are correct
   - Verify cluster name matches your Atlas cluster

3. **Test Connection**:
   ```bash
   python test_mongodb_connection.py
   ```
   This diagnostic script will help identify connection issues.

4. **Update Dependencies**:
   ```bash
   pip install --upgrade pymongo
   ```

### Blank Screen Issues

If the frontend shows a blank screen:

1. Check browser console (F12) for JavaScript errors
2. Verify frontend dev server is running: `npm run dev`
3. Check backend API is accessible: `http://localhost:5000/api/health`
4. Hard refresh the page (Ctrl+Shift+R)

### Collection Not Found

If collections don't appear:

1. Verify MongoDB connection is working
2. Check that collections exist in your MongoDB Atlas instance
3. Ensure the database user has read permissions
4. Check browser console for API errors

## 📝 License

MIT
