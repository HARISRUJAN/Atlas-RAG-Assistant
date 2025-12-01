/**
 * Type definitions for the RAG application
 */

export interface SourceReference {
  file_name: string;
  line_start: number;
  line_end: number;
  content: string;
  relevance_score: number;
}

export interface QueryResponse {
  answer: string;
  sources: SourceReference[];
  query: string;
}

export interface UploadResponse {
  message: string;
  document_id: string;
  file_name: string;
  total_chunks: number;
  stored_chunks: number;
}

export interface HealthStatus {
  status: string;
  mongodb: boolean;
  llm_api: boolean;
  mongodb_error?: string;
  llm_api_error?: string;
}

export interface UploadedFile {
  document_id: string;
  file_name: string;
  total_chunks: number;
  stored_chunks: number;
  selectedForIndex: boolean;
  upload_date: string;
}

export interface Collection {
  name: string;
}

export interface Database {
  name: string;
  collections: string[];
  collections_metadata?: Array<{
    name: string;
    type: 'origin' | 'semantic';
    is_semantic: boolean;
    size?: number;
    count?: number;
  }>;
}

export interface DatabasesResponse {
  databases: Database[];
}

// Connection types
export type Provider = 'mongo' | 'redis' | 'qdrant' | 'pinecone';
export type Scope = 'list.indexes' | 'read.metadata' | 'read.vectors' | 'write.vectors';

export interface Connection {
  connection_id: string;
  provider: Provider;
  display_name: string;
  scopes: Scope[];
  status: 'active' | 'inactive' | 'error';
  created_at: string;
}

export interface ConnectionCreateRequest {
  provider: Provider;
  display_name?: string;
  uri: string;
  api_key?: string;
}

export interface ConnectionConsentRequest {
  scopes: Scope[];
}

export interface ConnectionCollectionsResponse {
  connection_id: string;
  provider: Provider;
  collections: string[];
}

