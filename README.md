# MongoDB Atlas RAG System

A production-grade **Retrieval-Augmented Generation (RAG)** system with MongoDB Atlas Vector Search integration.

## Project Overview

This system implements a complete RAG pipeline that:
- Processes and chunks documents with line number preservation
- Generates embeddings using local sentence-transformers models
- Stores vectors in MongoDB Atlas with semantic search capabilities
- Retrieves contextually relevant chunks using vector similarity
- Generates accurate, source-cited answers using LLM APIs
- Supports multiple MongoDB databases and collections
- Dynamic question generation based on collection content
- Hierarchical collection browser with tree view

## Prerequisites

- **Python 3.11+** (with pip)
- **Node.js 18+** (with npm)
- **MongoDB Atlas account** (free tier available)
- **LLM API access** (Llama 3.2 or compatible OpenAI-compatible API)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd mongo_rag
```

### 2. Backend Setup

Create and activate a virtual environment:

**Windows:**
```bash
python -m venv rag_env
rag_env\Scripts\activate
```

**macOS/Linux:**
```bash
python -m venv rag_env
source rag_env/bin/activate
```

Install Python dependencies:
```bash
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

## Configuration

### Environment Variables

Create a `.env` file in the project root directory (same level as `README.md`):

```env
# MongoDB Atlas Connection String
# Get this from MongoDB Atlas → Connect → Connect your application
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster-name>.<region>.mongodb.net/?retryWrites=true&w=majority

# MongoDB Database Configuration
MONGODB_DATABASE_NAME=rag_database
MONGODB_COLLECTION_NAME=documents
MONGODB_VECTOR_INDEX_NAME=vector_index

# Two-Stage Pipeline Configuration (optional)
RAW_DOCUMENTS_DATABASE_NAME=rag_database
RAW_DOCUMENTS_COLLECTION_NAME=raw_documents
VECTOR_DATA_DATABASE_NAME=rag_database
VECTOR_DATA_COLLECTION_NAME=vector_data
VECTOR_DATA_INDEX_NAME=vector_index

# LLM API Configuration
LLM_API_URL=https://your-llama-api.com/v1/chat/completions
LLM_API_KEY=your-api-key-here
LLM_MODEL=llama3.2:latest

# Embedding Configuration
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# File Upload Configuration
MAX_FILE_SIZE_MB=10
ALLOWED_EXTENSIONS=pdf,txt,docx,md

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
FLASK_PORT=5000
```

**Important:**
- Replace `<username>`, `<password>`, and `<cluster-name>` with your actual MongoDB Atlas credentials
- Never commit the `.env` file to version control (it's already in `.gitignore`)
- The `.env` file should be in the project root directory

### Where to Enter Configuration

1. **Create `.env` file**: In the project root directory (same folder as `README.md`, `requirements.txt`, etc.)
2. **Copy the template above** into your `.env` file
3. **Replace placeholder values** with your actual credentials

## MongoDB Atlas Vector Index Setup

Before running queries, you must create a vector search index in MongoDB Atlas:

### Step 1: Access MongoDB Atlas

1. Go to [MongoDB Atlas](https://cloud.mongodb.com)
2. Log in to your account
3. Navigate to your cluster

### Step 2: Create Vector Search Index

1. Click on the **"Search"** tab (NOT "Collections" or "Indexes")
2. Click **"Create Search Index"**
3. Select **"JSON Editor"**
4. Paste this configuration:

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 384,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "document_id"
    },
    {
      "type": "filter",
      "path": "file_name"
    }
  ]
}
```

5. Set the following:
   - **Index Name**: `vector_index` (or match your `VECTOR_DATA_INDEX_NAME` in `.env`)
   - **Database Name**: Your database name (e.g., `rag_database`)
   - **Collection Name**: Your collection name (e.g., `documents` or `vector_data`)

6. Click **"Create Search Index"**
7. Wait 1-3 minutes for the index status to change from "Building" to "Active"

**Note:** The index name must match the `VECTOR_DATA_INDEX_NAME` or `MONGODB_VECTOR_INDEX_NAME` value in your `.env` file.

## Running the Application

### Option 1: Using the Startup Script (Recommended)

From the project root directory:

```bash
python start_project.py
```

This will:
- Start the Flask backend server on port 5000 (or port specified in `.env`)
- Display connection information
- Provide instructions to start the frontend in a separate terminal

Then, in a **new terminal window**, start the frontend:

```bash
cd frontend
npm run dev
```

### Option 2: Manual Startup

**Terminal 1 - Backend:**
```bash
# From project root, with virtual environment activated
python -m flask --app backend.app run --port 5000
```

Or using the app directly:
```bash
python -m backend.app
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### Access the Application

- **Frontend**: `http://localhost:5173` (or the port shown in the terminal)
- **Backend API**: `http://localhost:5000/api`
- **Health Check**: `http://localhost:5000/api/health`

## File Structure

```
mongo_rag/
├── backend/                      # Flask backend application
│   ├── app.py                    # Main Flask application entry point
│   ├── config.py                 # Configuration management (reads .env)
│   ├── models/                   # Data models
│   │   ├── document.py          # Document chunk model
│   │   ├── query.py             # Query request/response models
│   │   ├── raw_document.py      # Raw document model
│   │   ├── connection.py        # Connection model
│   │   └── origin_source.py     # Origin source model
│   ├── routes/                   # API route handlers
│   │   ├── query.py             # Query endpoint
│   │   ├── upload.py            # File upload endpoint
│   │   ├── collections.py       # Collections listing endpoint
│   │   ├── ingestion.py         # Document ingestion endpoint
│   │   ├── health.py            # Health check endpoint
│   │   ├── config.py            # Configuration endpoint
│   │   ├── connections.py       # Connection management
│   │   └── origin.py            # Origin source management
│   ├── services/                 # Business logic services
│   │   ├── rag_service.py       # RAG pipeline orchestration
│   │   ├── embedding_service.py # Embedding generation
│   │   ├── vector_store.py      # Vector store operations
│   │   ├── vector_data_store.py # Vector data collection operations
│   │   ├── document_processor.py # Document processing
│   │   ├── ingestion_pipeline.py # Ingestion pipeline
│   │   ├── raw_document_store.py # Raw document storage
│   │   ├── collection_service.py # Collection validation
│   │   ├── unified_vector_store.py # Multi-provider support
│   │   ├── realtime_ingestion.py # Real-time ingestion
│   │   ├── providers/            # Vector store providers
│   │   │   ├── mongodb.py        # MongoDB provider
│   │   │   ├── redis.py          # Redis provider
│   │   │   ├── pinecone.py       # Pinecone provider
│   │   │   └── qdrant.py         # Qdrant provider
│   │   └── origin_sources/       # Origin source handlers
│   │       ├── mongodb_origin.py # MongoDB origin
│   │       ├── filesystem_origin.py # Filesystem origin
│   │       └── qdrant_origin.py  # Qdrant origin
│   └── utils/                    # Utility functions
│       ├── chunking.py           # Text chunking utilities
│       ├── file_validator.py     # File validation
│       ├── mongodb_client.py     # MongoDB connection utilities
│       └── setup_pipeline_collections.py # Collection setup
├── frontend/                     # React frontend application
│   ├── src/
│   │   ├── App.tsx               # Main application component
│   │   ├── api.ts                # API client
│   │   ├── types.ts              # TypeScript type definitions
│   │   └── components/          # React components
│   │       ├── QueryInput.tsx    # Query input component
│   │       ├── ResponseDisplay.tsx # Response display
│   │       ├── CollectionSelector.tsx # Collection selector
│   │       ├── DatabaseCollectionSelector.tsx # Database/collection tree
│   │       ├── IngestionPanel.tsx # Ingestion panel
│   │       ├── IngestionPipelinePanel.tsx # Pipeline panel
│   │       ├── RawDocumentList.tsx # Raw document list
│   │       └── ...               # Other components
│   ├── package.json              # Frontend dependencies
│   └── vite.config.ts            # Vite configuration
├── requirements.txt               # Python dependencies
├── start_project.py              # Startup script
├── docker-compose.yml            # Docker Compose configuration
├── Dockerfile.backend            # Backend Docker image
├── Dockerfile.frontend           # Frontend Docker image
├── nginx.conf                    # Nginx configuration
├── run.bat                       # Windows run script
├── run.sh                        # Linux/Mac run script
├── START_SYSTEM.bat              # Windows system start script
└── README.md                     # This file
```

## Usage Guide

### 1. Upload Documents

- Use the file upload panel in the right sidebar
- Supported formats: PDF, TXT, DOCX, MD
- Maximum file size: 10MB (configurable in `.env`)

### 2. Process Documents

- Documents are automatically processed and chunked
- Embeddings are generated and stored in MongoDB
- Processed documents appear in the ingestion pipeline

### 3. Query Documents

- Select a collection from the left sidebar
- Enter your question in the query input
- View the answer with source citations
- Suggested questions are generated based on the collection content

### 4. Browse Collections

- Left sidebar shows all databases and collections
- Expand/collapse databases to view collections
- Select a collection to query its documents

## Troubleshooting

### MongoDB Connection Issues

**Error: "Failed to connect to MongoDB"**

1. **Check IP Whitelist:**
   - Go to MongoDB Atlas → Network Access
   - Add your current IP address or `0.0.0.0/0` (for testing only)
   - Wait 1-2 minutes for changes to propagate

2. **Verify Connection String:**
   - Ensure format: `mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority`
   - Check username and password are correct
   - Verify cluster name matches your Atlas cluster
   - Ensure password is URL-encoded if it contains special characters

3. **Update Dependencies:**
   ```bash
   pip install --upgrade pymongo
   ```

### Vector Search Not Working

**Error: "Collection does not have a vector index"**

1. Verify the vector search index exists in MongoDB Atlas
2. Check index name matches `VECTOR_DATA_INDEX_NAME` in `.env`
3. Ensure index status is "Active" (not "Building")
4. Verify index configuration includes `embedding` field with 384 dimensions

### Frontend Not Loading

**Blank screen or connection errors:**

1. Check browser console (F12) for JavaScript errors
2. Verify frontend dev server is running: `npm run dev`
3. Check backend API is accessible: `http://localhost:5000/api/health`
4. Hard refresh the page (Ctrl+Shift+R or Cmd+Shift+R)
5. Verify CORS settings in `backend/app.py` include your frontend port

### Backend Not Starting

**Error: "ModuleNotFoundError" or import errors:**

1. Ensure virtual environment is activated
2. Install dependencies: `pip install -r requirements.txt`
3. Verify Python version: `python --version` (should be 3.11+)
4. Check `.env` file exists and is in the project root

### No Results from Queries

**Query returns "No results found":**

1. Verify documents have been uploaded and processed
2. Check collection has documents with embeddings
3. Ensure vector search index is created and active
4. Verify index name in `.env` matches the index in MongoDB Atlas
5. Check embedding dimensions match (should be 384 for all-MiniLM-L6-v2)

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend Framework** | Flask (Python) |
| **Vector Database** | MongoDB Atlas Vector Search |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) |
| **LLM** | Llama 3.2 (or compatible API) |
| **Frontend** | React + TypeScript + Vite |
| **Styling** | Tailwind CSS |
| **Document Processing** | PyPDF2, python-docx, markdown |
