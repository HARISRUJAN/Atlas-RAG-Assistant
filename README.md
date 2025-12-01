# Unified Multi-Provider RAG System

A production-grade **Retrieval-Augmented Generation (RAG)** system with unified support for multiple vector store providers and flexible data ingestion pipelines.

## Project Overview

This system implements a complete, unified RAG pipeline that:

### Core RAG Capabilities
- Processes and chunks documents with line number preservation
- Generates embeddings using local sentence-transformers models
- Retrieves contextually relevant chunks using vector similarity
- Generates accurate, source-cited answers using LLM APIs
- Dynamic question generation based on collection content
- Hierarchical collection browser with tree view

### Unified Multi-Provider Architecture
- **Multiple Vector Store Support**: Works with MongoDB Atlas, Redis, Qdrant, and Pinecone through a unified interface
- **Connection Management**: Secure, encrypted credential storage and management for multiple data sources
- **Multi-Collection Querying**: Query across multiple collections and providers simultaneously
- **Provider Abstraction**: Switch between vector stores without changing application code

### Flexible Data Ingestion
- **Origin Sources**: Ingest data from MongoDB collections, Qdrant, filesystem, or direct file uploads
- **Two-Stage Pipeline**: Raw documents → Vector data workflow with deduplication
- **Semantic Collections**: Automatic semantic collection management with origin/semantic separation
- **Real-time Ingestion**: Optional real-time document ingestion using MongoDB Change Streams

### Collection Architecture
- **Origin Collections**: Source data collections (e.g., `movies`, `documents`)
- **Semantic Collections**: Vector-enabled collections with `_semantic` suffix (e.g., `movies_semantic`)
- **Automatic Naming**: System automatically manages semantic collection naming
- **Multi-Database Support**: Work with collections across multiple databases

## Prerequisites

- **Python 3.11+** (with pip)
- **Node.js 18+** (with npm)
- **MongoDB Atlas account** (free tier available) - Required for default setup and connection storage
- **LLM API access** (Llama 3.2 or compatible OpenAI-compatible API)
- **Vector Store Provider** (optional): One or more of:
  - MongoDB Atlas (recommended, included)
  - Redis with RedisSearch
  - Qdrant instance
  - Pinecone account

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
# MongoDB Atlas Connection String (Primary/Default)
# Get this from MongoDB Atlas → Connect → Connect your application
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster-name>.<region>.mongodb.net/?retryWrites=true&w=majority

# MongoDB Database Configuration (Legacy/Default)
MONGODB_DATABASE_NAME=rag_database
MONGODB_COLLECTION_NAME=documents
MONGODB_VECTOR_INDEX_NAME=vector_index

# Two-Stage Pipeline Configuration
RAW_DOCUMENTS_DATABASE_NAME=rag_database
RAW_DOCUMENTS_COLLECTION_NAME=raw_documents
VECTOR_DATA_DATABASE_NAME=rag_database
VECTOR_DATA_COLLECTION_NAME=vector_data
VECTOR_DATA_INDEX_NAME=vector_index

# Semantic Collection Architecture
# Origin collections store source data, semantic collections store vectors
# System automatically appends '_semantic' suffix to create semantic collections
ORIGIN_DB_NAME=rag_database
ORIGIN_COLLECTION_NAME=collection_data

# Connection Encryption (Optional)
# If not set, system generates key from MONGODB_URI
CONNECTION_ENCRYPTION_KEY=your-encryption-key-here

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
- `MONGODB_URI` is used as the default connection, but you can add more connections via the API

### Connection Management

Connections to vector store providers are managed through the API and stored securely in MongoDB:

- **Supported Providers**: `mongo`, `redis`, `qdrant`, `pinecone`
- **Credential Storage**: All credentials are encrypted before storage
- **Connection Scopes**: Control permissions (list.indexes, read.metadata, read.vectors, write.vectors)
- **Connection Testing**: Test connections before saving

Connections are created via the API (see [Connection Management](#connection-management) section) and stored in the `rag_database.connections` collection.

### Origin Source Configuration

Origin sources define where your data originates before ingestion:

- **MongoDB Origin**: Read from MongoDB collections
  - Required: `uri`, `database_name`, `collection_name`
- **Qdrant Origin**: Read from Qdrant collections
  - Required: `uri`, `collection_name`, optional `api_key`
- **Filesystem Origin**: Read files from directory
  - Required: `base_path`
- **File Upload**: Direct file uploads
  - No configuration needed

Origin sources are configured per-ingestion request or can be managed via the API.

### Semantic Collection Naming

The system uses a semantic collection architecture:

- **Origin Collections**: Source data (e.g., `movies`, `documents`)
- **Semantic Collections**: Vector-enabled collections (e.g., `movies_semantic`, `documents_semantic`)
- **Automatic Naming**: System automatically appends `_semantic` suffix
- **Collection Format**: Can use `database.collection` format (e.g., `srugenai_db.movies_semantic`)

When querying, you can specify either:
- Origin collection name (system finds corresponding semantic collection)
- Semantic collection name directly
- Full path: `database.collection` or `database.collection_semantic`

### Where to Enter Configuration

1. **Create `.env` file**: In the project root directory (same folder as `README.md`, `requirements.txt`, etc.)
2. **Copy the template above** into your `.env` file
3. **Replace placeholder values** with your actual credentials
4. **Create connections** via the API or UI for additional vector store providers

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

## Connection Management

The system supports multiple vector store providers through a unified connection management system. Connections are stored securely with encrypted credentials.

### Supported Providers

- **MongoDB** (`mongo`): MongoDB Atlas or self-hosted MongoDB with vector search
- **Redis** (`redis`): Redis with RedisSearch module
- **Qdrant** (`qdrant`): Qdrant vector database
- **Pinecone** (`pinecone`): Pinecone managed vector database

### Creating a Connection

Connections can be created via the API or UI:

**API Example:**
```bash
POST /api/connections
{
  "provider": "mongo",
  "display_name": "Production MongoDB",
  "uri": "mongodb+srv://user:pass@cluster.mongodb.net/",
  "api_key": null
}
```

**Connection Scopes:**
- `list.indexes`: List available collections/indexes
- `read.metadata`: Read collection metadata
- `read.vectors`: Read vector data
- `write.vectors`: Write vector data

### Managing Connections

- **List Connections**: `GET /api/connections`
- **Get Connection**: `GET /api/connections/<connection_id>`
- **Test Connection**: `POST /api/connections/<connection_id>/test`
- **Update Scopes**: `POST /api/connections/<connection_id>/consent`
- **List Collections**: `GET /api/connections/<connection_id>/collections`
- **Delete Connection**: `DELETE /api/connections/<connection_id>`

### Using Connections in Queries

When querying, you can specify multiple connections and collections:

```json
{
  "query": "What is machine learning?",
  "connection_ids": ["conn-1", "conn-2"],
  "collection_names": ["conn-1:database.collection", "conn-2:index_name"]
}
```

## Origin Sources

Origin sources define where your data originates before being ingested into the RAG system. The system supports multiple origin source types.

### Supported Origin Sources

#### 1. MongoDB Origin
Read documents from MongoDB collections.

**Configuration:**
```json
{
  "source_type": "mongodb",
  "connection_config": {
    "uri": "mongodb+srv://...",
    "database_name": "sample_mflix",
    "collection_name": "movies"
  }
}
```

**Features:**
- Reads documents from any MongoDB collection
- Supports filtering and pagination
- Automatically handles document structure
- Cannot use semantic collections as origin (must use origin collections)

#### 2. Qdrant Origin
Read documents from Qdrant collections.

**Configuration:**
```json
{
  "source_type": "qdrant",
  "connection_config": {
    "uri": "http://localhost:6333",
    "api_key": "optional-key",
    "collection_name": "documents"
  }
}
```

#### 3. Filesystem Origin
Read files from a directory.

**Configuration:**
```json
{
  "source_type": "filesystem",
  "connection_config": {
    "base_path": "/path/to/documents"
  }
}
```

**Supported Formats:** PDF, TXT, DOCX, MD

#### 4. File Upload
Direct file uploads through the UI or API.

**No configuration needed** - files are uploaded directly.

### Using Origin Sources

**List Available Source Types:**
```bash
GET /api/origin/sources
```

**Test Connection:**
```bash
POST /api/origin/connect
{
  "source_type": "mongodb",
  "connection_config": {...}
}
```

**List Documents:**
```bash
POST /api/origin/mongodb/documents
{
  "connection_config": {...},
  "limit": 100,
  "skip": 0
}
```

**Get Specific Document:**
```bash
POST /api/origin/mongodb/documents/<origin_id>
{
  "connection_config": {...}
}
```

## Ingestion Pipeline

The system uses a two-stage ingestion pipeline for robust document processing and deduplication.

### Pipeline Stages

#### Stage 1: Raw Documents Collection
- **Purpose**: Store original documents before processing
- **Collection**: `raw_documents` (configurable)
- **Features**:
  - Document deduplication by origin ID
  - Status tracking (pending, processing, processed, failed)
  - Origin source metadata preservation
  - Retry capability for failed documents

#### Stage 2: Vector Data Collection
- **Purpose**: Store processed, chunked, and embedded documents
- **Collection**: Semantic collections (e.g., `collection_name_semantic`)
- **Features**:
  - Chunked document storage
  - Vector embeddings
  - Line number preservation
  - Source references

### Ingestion Workflow

1. **Ingest from Origin**: Document is fetched from origin source
2. **Store Raw**: Document stored in `raw_documents` with status `pending`
3. **Process**: Document is chunked and embedded
4. **Store Vectors**: Chunks stored in semantic collection
5. **Update Status**: Raw document status updated to `processed`

### Ingestion Methods

#### 1. Ingest from Origin Source
```bash
POST /api/ingest/origin
{
  "origin_source_type": "mongodb",
  "origin_id": "document_id",
  "connection_config": {...},
  "skip_duplicates": true
}
```

#### 2. Batch Ingestion
```bash
POST /api/ingest/origin
{
  "origin_source_type": "mongodb",
  "origin_ids": ["id1", "id2", "id3"],
  "connection_config": {...},
  "skip_duplicates": true
}
```

#### 3. Process Raw Document
```bash
POST /api/ingest/process
{
  "raw_document_id": "raw_doc_id",
  "target_collection": "database.collection_semantic"
}
```

#### 4. Batch Process
```bash
POST /api/ingest/process/batch
{
  "raw_document_ids": ["id1", "id2"],
  "target_collection": "database.collection_semantic"
}
```

### Monitoring Ingestion

**List Raw Documents:**
```bash
GET /api/ingest/raw?status=pending&limit=100
```

**Get Raw Document:**
```bash
GET /api/ingest/raw/<raw_document_id>
```

**Get Ingestion Status:**
```bash
GET /api/ingest/status
```

## Semantic Collections

The system uses a semantic collection architecture to separate source data from vector data.

### Collection Types

#### Origin Collections
- **Purpose**: Store original, unprocessed source data
- **Examples**: `movies`, `documents`, `products`
- **Features**: 
  - Original document structure preserved
  - No vector embeddings
  - Used as origin sources for ingestion

#### Semantic Collections
- **Purpose**: Store processed, vector-enabled data
- **Naming**: Automatically named with `_semantic` suffix
- **Examples**: `movies_semantic`, `documents_semantic`
- **Features**:
  - Chunked documents
  - Vector embeddings
  - Vector search indexes
  - Used for RAG queries

### Collection Naming Rules

1. **Origin collections** use their natural name (e.g., `movies`)
2. **Semantic collections** automatically get `_semantic` suffix (e.g., `movies_semantic`)
3. **Full path format**: `database.collection` or `database.collection_semantic`
4. **System automatically resolves** origin → semantic when needed

### Working with Collections

**Query by Origin Collection:**
```json
{
  "query": "What is...?",
  "collection_name": "movies"  // System finds movies_semantic
}
```

**Query by Semantic Collection:**
```json
{
  "query": "What is...?",
  "collection_name": "movies_semantic"  // Direct access
}
```

**Query with Database:**
```json
{
  "query": "What is...?",
  "collection_name": "srugenai_db.movies_semantic"
}
```

**Multi-Collection Query:**
```json
{
  "query": "What is...?",
  "collection_names": [
    "database1.collection1_semantic",
    "database2.collection2_semantic"
  ]
}
```

### Collection Validation

The system validates collections before operations:
- Checks if collection exists
- Verifies vector index exists for semantic collections
- Validates collection type (origin vs semantic)
- Ensures proper naming conventions

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
│   │   ├── connection.py        # Connection model (multi-provider)
│   │   └── origin_source.py     # Origin source model
│   ├── routes/                   # API route handlers
│   │   ├── query.py             # Query endpoint (unified multi-provider)
│   │   ├── upload.py            # File upload endpoint
│   │   ├── collections.py       # Collections listing endpoint
│   │   ├── ingestion.py         # Document ingestion endpoint
│   │   ├── health.py            # Health check endpoint
│   │   ├── config.py            # Configuration endpoint
│   │   ├── connections.py       # Connection management (CRUD)
│   │   └── origin.py            # Origin source management
│   ├── services/                 # Business logic services
│   │   ├── rag_service.py       # RAG pipeline orchestration (unified)
│   │   ├── embedding_service.py # Embedding generation
│   │   ├── vector_store.py      # Legacy vector store operations
│   │   ├── vector_data_store.py # Vector data collection operations
│   │   ├── document_processor.py # Document processing
│   │   ├── ingestion_pipeline.py # Two-stage ingestion pipeline
│   │   ├── raw_document_store.py # Raw document storage
│   │   ├── collection_service.py # Collection validation
│   │   ├── unified_vector_store.py # Multi-provider unified interface
│   │   ├── realtime_ingestion.py # Real-time ingestion (Change Streams)
│   │   ├── providers/            # Vector store provider implementations
│   │   │   ├── __init__.py      # Provider factory
│   │   │   ├── base.py          # Base provider interface
│   │   │   ├── mongodb.py        # MongoDB provider
│   │   │   ├── redis.py          # Redis provider
│   │   │   ├── pinecone.py       # Pinecone provider
│   │   │   └── qdrant.py         # Qdrant provider
│   │   └── origin_sources/       # Origin source implementations
│   │       ├── __init__.py      # Origin source factory
│   │       ├── base.py          # Base origin source interface
│   │       ├── mongodb_origin.py # MongoDB origin source
│   │       ├── filesystem_origin.py # Filesystem origin source
│   │       └── qdrant_origin.py  # Qdrant origin source
│   └── utils/                    # Utility functions
│       ├── chunking.py           # Text chunking utilities
│       ├── file_validator.py     # File validation
│       ├── mongodb_client.py     # MongoDB connection utilities
│       ├── setup_pipeline_collections.py # Collection setup
│       └── setup_semantic_indexes.py # Semantic index setup
├── frontend/                     # React frontend application
│   ├── src/
│   │   ├── App.tsx               # Main application component
│   │   ├── api.ts                # API client (unified endpoints)
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
├── check_vector_index.py         # Vector index validation utility
├── setup_vector_index_for_collection.py # Index setup utility
└── README.md                     # This file
```

## Usage Guide

### 1. Set Up Connections (Optional)

If you want to use multiple vector store providers or connect to different MongoDB instances:

1. **Create a Connection**:
   - Use the connection management UI or API
   - Select provider type (mongo, redis, qdrant, pinecone)
   - Enter connection URI and credentials
   - Test the connection before saving
   - Grant appropriate scopes (permissions)

2. **Manage Connections**:
   - View all connections in the connections panel
   - Test connection status
   - Update scopes as needed
   - List available collections for each connection

**Note**: If you only use the default MongoDB connection from `.env`, you can skip this step.

### 2. Ingest Documents

There are multiple ways to ingest documents into the system:

#### Option A: Direct File Upload
- Use the file upload panel in the right sidebar
- Supported formats: PDF, TXT, DOCX, MD
- Maximum file size: 10MB (configurable in `.env`)
- Files are automatically processed through the pipeline

#### Option B: Ingest from MongoDB Collection
1. **Configure Origin Source**:
   - Select "MongoDB" as origin source type
   - Enter MongoDB URI, database name, and collection name
   - Test the connection

2. **Browse Documents**:
   - View available documents in the origin collection
   - Select documents to ingest

3. **Ingest Documents**:
   - Choose single or batch ingestion
   - Documents are stored in `raw_documents` first
   - Then processed into semantic collections

#### Option C: Ingest from Other Sources
- **Qdrant**: Configure Qdrant origin source
- **Filesystem**: Point to a directory with documents
- **API**: Use ingestion API endpoints directly

### 3. Process Raw Documents

After ingesting documents, process them into vector data:

1. **View Raw Documents**:
   - Open the ingestion pipeline panel
   - See all raw documents with their status
   - Filter by status (pending, processing, processed, failed)

2. **Process Documents**:
   - Select target semantic collection
   - Process single document or batch
   - Monitor processing status
   - Retry failed documents if needed

### 4. Query Documents

Query your semantic collections using natural language:

1. **Select Collection(s)**:
   - Choose from the collection browser (left sidebar)
   - Collections are organized by database
   - Semantic collections are marked with `_semantic` suffix
   - You can query multiple collections simultaneously

2. **Enter Query**:
   - Type your question in the query input
   - Use suggested questions based on collection content
   - Submit the query

3. **View Results**:
   - See the generated answer with source citations
   - View source documents with line numbers
   - Check relevance scores
   - Navigate to source documents

### 5. Multi-Collection Queries

Query across multiple collections or connections:

1. **Select Multiple Collections**:
   - Use the collection selector
   - Choose collections from different databases
   - Mix collections from different connections

2. **Unified Results**:
   - System aggregates results from all collections
   - Ranks results by relevance across all sources
   - Provides unified answer with multiple source citations

### 6. Browse Collections

- **Database Tree View**: Left sidebar shows hierarchical database/collection structure
- **Collection Types**: Origin collections and semantic collections are clearly marked
- **Collection Metadata**: View collection size, document count, and type
- **Quick Access**: Click to select collection for querying

### 7. Monitor Ingestion Pipeline

- **Raw Documents Panel**: View all ingested documents
- **Status Tracking**: Monitor pending, processing, processed, and failed documents
- **Retry Failed**: Retry processing for failed documents
- **Batch Operations**: Process multiple documents at once

## API Endpoints

The system provides a comprehensive REST API for all operations.

### Core Endpoints

#### Health Check
```bash
GET /api/health
```
Returns system health status including MongoDB and LLM API connectivity.

#### API Information
```bash
GET /api
```
Returns API version and available endpoints.

### Query Endpoints

#### Query Documents
```bash
POST /api/query
Content-Type: application/json

{
  "query": "Your question here",
  "collection_name": "collection_name" | "database.collection",
  "collection_names": ["collection1", "collection2"],  // Multi-collection
  "connection_ids": ["conn-1", "conn-2"],  // Multi-provider
  "top_k": 5
}
```

**Response:**
```json
{
  "answer": "Generated answer...",
  "sources": [
    {
      "file_name": "document.pdf",
      "line_start": 10,
      "line_end": 15,
      "content": "Source text...",
      "relevance_score": 0.95
    }
  ],
  "query": "Your question here"
}
```

#### Get Collection Questions
```bash
GET /api/collections/<collection_name>/questions
```
Returns suggested questions based on collection content.

### Connection Management Endpoints

#### Create Connection
```bash
POST /api/connections
{
  "provider": "mongo|redis|qdrant|pinecone",
  "display_name": "Connection Name",
  "uri": "connection_string",
  "api_key": "optional_api_key"
}
```

#### List Connections
```bash
GET /api/connections
```

#### Get Connection
```bash
GET /api/connections/<connection_id>
```

#### Test Connection
```bash
POST /api/connections/<connection_id>/test
```

#### Update Connection Scopes
```bash
POST /api/connections/<connection_id>/consent
{
  "scopes": ["list.indexes", "read.metadata", "read.vectors", "write.vectors"]
}
```

#### List Connection Collections
```bash
GET /api/connections/<connection_id>/collections
```

#### Delete Connection
```bash
DELETE /api/connections/<connection_id>
```

### Origin Source Endpoints

#### List Source Types
```bash
GET /api/origin/sources
```

#### Test Origin Connection
```bash
POST /api/origin/connect
{
  "source_type": "mongodb|qdrant|filesystem",
  "connection_config": {...}
}
```

#### List Origin Documents
```bash
POST /api/origin/<source_type>/documents
{
  "connection_config": {...},
  "limit": 100,
  "skip": 0
}
```

#### Get Origin Document
```bash
POST /api/origin/<source_type>/documents/<origin_id>
{
  "connection_config": {...}
}
```

### Ingestion Endpoints

#### Ingest from Origin
```bash
POST /api/ingest/origin
{
  "origin_source_type": "mongodb|qdrant|filesystem",
  "origin_id": "document_id",  // Single
  "origin_ids": ["id1", "id2"],  // Batch
  "connection_config": {...},
  "skip_duplicates": true
}
```

#### List Raw Documents
```bash
GET /api/ingest/raw?status=pending&limit=100&skip=0
```

#### Get Raw Document
```bash
GET /api/ingest/raw/<raw_document_id>
```

#### Process Raw Document
```bash
POST /api/ingest/process
{
  "raw_document_id": "raw_doc_id",
  "target_collection": "database.collection_semantic"
}
```

#### Batch Process
```bash
POST /api/ingest/process/batch
{
  "raw_document_ids": ["id1", "id2"],
  "target_collection": "database.collection_semantic"
}
```

#### Get Ingestion Status
```bash
GET /api/ingest/status
```

### Collection Endpoints

#### List Databases and Collections
```bash
GET /api/collections
```

**Response:**
```json
{
  "databases": [
    {
      "name": "database_name",
      "collections": ["collection1", "collection2"],
      "collections_metadata": [
        {
          "name": "collection1",
          "type": "origin|semantic",
          "is_semantic": false,
          "size": 1024,
          "count": 100
        }
      ]
    }
  ]
}
```

### Configuration Endpoints

#### Get MongoDB URI
```bash
GET /api/config/mongodb-uri
```

#### Set MongoDB URI
```bash
POST /api/config/mongodb-uri
{
  "mongodb_uri": "mongodb+srv://..."
}
```

### Upload Endpoints

#### Upload File
```bash
POST /api/upload
Content-Type: multipart/form-data

file: <file>
collection_name: "target_collection"
```

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
6. For multi-collection queries, verify all collections are semantic collections
7. Check connection status if using multiple providers

### Connection Management Issues

**Error: "Connection test failed"**

1. Verify connection URI format is correct for the provider
2. Check network connectivity to the vector store
3. Verify credentials (username, password, API keys)
4. For MongoDB: Ensure IP whitelist includes your IP
5. For Qdrant/Pinecone: Verify API keys are valid
6. Check provider-specific requirements (e.g., RedisSearch module for Redis)

**Error: "Connection not found"**

1. Verify connection was created successfully
2. Check connection ID is correct
3. Ensure connection storage database is accessible
4. Try listing all connections to verify

### Origin Source Issues

**Error: "Failed to connect to origin source"**

1. Verify connection_config contains all required fields
2. For MongoDB: Check URI, database_name, and collection_name
3. For Qdrant: Verify URI and collection_name
4. For filesystem: Check base_path exists and is readable
5. Ensure origin collection is not a semantic collection (use origin collections only)

**Error: "Document not found in origin"**

1. Verify origin_id is correct
2. Check document exists in the origin source
3. Verify connection_config points to the correct source
4. For MongoDB: Check database and collection names

### Ingestion Pipeline Issues

**Error: "Raw document processing failed"**

1. Check raw document status in the ingestion panel
2. Verify target collection exists and is a semantic collection
3. Ensure vector index is created for the target collection
4. Check document content is valid and can be processed
5. Review error messages in the raw document metadata

**Error: "Duplicate document skipped"**

1. This is expected behavior when `skip_duplicates=true`
2. Check existing raw document to see if it was already processed
3. Use different origin_id if you want to ingest the same document again
4. Process the existing raw document instead of re-ingesting

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend Framework** | Flask (Python) |
| **Vector Databases** | MongoDB Atlas Vector Search (primary), Redis, Qdrant, Pinecone |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) |
| **LLM** | Llama 3.2 (or compatible OpenAI-compatible API) |
| **Frontend** | React + TypeScript + Vite |
| **Styling** | Tailwind CSS |
| **Document Processing** | PyPDF2, python-docx, markdown |
| **Encryption** | Fernet (symmetric encryption for credentials) |
| **Real-time Processing** | MongoDB Change Streams |

### Supported Vector Store Providers

- **MongoDB**: MongoDB Atlas or self-hosted MongoDB with vector search
- **Redis**: Redis with RedisSearch module
- **Qdrant**: Qdrant vector database (self-hosted or cloud)
- **Pinecone**: Pinecone managed vector database

### Supported Origin Sources

- **MongoDB Collections**: Read from any MongoDB collection
- **Qdrant Collections**: Read from Qdrant collections
- **Filesystem**: Read files from local or network directories
- **File Upload**: Direct file uploads via API or UI


