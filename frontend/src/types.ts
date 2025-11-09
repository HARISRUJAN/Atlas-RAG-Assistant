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
}

export interface DatabasesResponse {
  databases: Database[];
}

