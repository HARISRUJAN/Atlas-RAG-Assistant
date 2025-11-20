/**
 * API service for communicating with the Flask backend
 */

import axios from 'axios';
import type { 
  QueryResponse, UploadResponse, HealthStatus, Database,
  Connection, ConnectionCreateRequest, ConnectionCollectionsResponse
} from './types';

// Use relative URL to leverage Vite proxy (configured in vite.config.ts to proxy to port 5002)
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
});

// Add response interceptor for better error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ERR_NETWORK' || error.message === 'Network Error' || !error.response) {
      const backendUrl = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';
      const baseUrl = backendUrl.replace('/api', '');
      error.message = `Cannot connect to backend server. Please ensure the backend is running on ${baseUrl}`;
    }
    return Promise.reject(error);
  }
);

export const apiService = {
  /**
   * Upload a file for processing
   */
  async uploadFile(file: File, connectionId?: string, mongodbUri?: string): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (connectionId) {
      formData.append('connection_id', connectionId);
    }
    
    const headers: Record<string, string> = {
      'Content-Type': 'multipart/form-data',
    };
    if (mongodbUri) {
      headers['X-MongoDB-URI'] = mongodbUri;
    }
    if (connectionId) {
      headers['X-Connection-ID'] = connectionId;
    }
    
    const response = await api.post<UploadResponse>('/upload', formData, { headers });
    
    return response.data;
  },

  /**
   * Query the RAG system
   * collectionNames can be a single string (for backward compatibility) or an array of strings
   */
  async query(
    query: string, 
    topK: number = 5, 
    collectionNames?: string | string[], 
    connectionIds?: string[],
    mongodbUri?: string,
    vectorCollection?: string
  ): Promise<QueryResponse> {
    const headers: Record<string, string> = {};
    if (mongodbUri) {
      headers['X-MongoDB-URI'] = mongodbUri;
    }
    
    // Support both single collection (backward compatibility) and multiple collections
    const payload: any = {
      query,
      top_k: topK,
      use_pipeline: true,
    };
    
    if (connectionIds && connectionIds.length > 0) {
      payload.connection_ids = connectionIds;
    }
    
    if (Array.isArray(collectionNames)) {
      payload.collection_names = collectionNames;
    } else if (collectionNames) {
      // Backward compatibility: single string becomes collection_name
      payload.collection_name = collectionNames;
    }
    
    // Add vector_collection for pipeline mode (database.collection format, e.g., "srugenai_db.movies")
    if (vectorCollection) {
      payload.vector_collection = vectorCollection;
    }
    
    const response = await api.post<QueryResponse>('/query', payload, { headers });
    
    return response.data;
  },

  /**
   * Get list of all MongoDB databases with their collections
   */
  async getDatabases(connectionId?: string, mongodbUri?: string): Promise<Database[]> {
    const headers: Record<string, string> = {};
    if (mongodbUri) {
      headers['X-MongoDB-URI'] = mongodbUri;
    }
    if (connectionId) {
      headers['X-Connection-ID'] = connectionId;
    }
    const response = await api.get<{ databases: Database[] }>('/collections', { headers });
    return response.data.databases;
  },

  /**
   * Get list of all MongoDB collections (legacy - returns flat list from all databases)
   */
  async getCollections(): Promise<string[]> {
    const databases = await this.getDatabases();
    // Flatten all collections from all databases
    const allCollections: string[] = [];
    databases.forEach(db => {
      db.collections.forEach(coll => {
        allCollections.push(`${db.name}.${coll}`);
      });
    });
    return allCollections;
  },

  /**
   * Get suggested questions for a collection
   * collectionName can be "collection" or "database.collection"
   */
  async getSuggestedQuestions(collectionName: string, mongodbUri?: string): Promise<string[]> {
    // URL encode the collection path in case it contains special characters
    const encodedPath = encodeURIComponent(collectionName);
    const headers: Record<string, string> = {};
    if (mongodbUri) {
      headers['X-MongoDB-URI'] = mongodbUri;
    }
    const response = await api.get<{ questions: string[] }>(`/collections/${encodedPath}/questions`, { headers });
    return response.data.questions;
  },

  /**
   * Check system health
   */
  async healthCheck(): Promise<HealthStatus> {
    const response = await api.get<HealthStatus>('/health');
    return response.data;
  },

  // Connection management methods
  /**
   * Create a new connection
   */
  async createConnection(data: ConnectionCreateRequest): Promise<{ connection_id: string; message: string }> {
    const response = await api.post<{ connection_id: string; message: string }>('/connections', data);
    return response.data;
  },

  /**
   * List all connections
   */
  async getConnections(): Promise<Connection[]> {
    const response = await api.get<{ connections: Connection[] }>('/connections');
    return response.data.connections;
  },

  /**
   * Get connection details
   */
  async getConnection(connectionId: string): Promise<Connection> {
    const response = await api.get<Connection>(`/connections/${connectionId}`);
    return response.data;
  },

  /**
   * Update connection scopes (consent)
   */
  async updateConnectionScopes(connectionId: string, scopes: string[]): Promise<Connection> {
    const response = await api.post<Connection>(`/connections/${connectionId}/consent`, { scopes });
    return response.data;
  },

  /**
   * Test connection
   */
  async testConnection(connectionId: string): Promise<{ connection_id: string; status: string; message: string }> {
    const response = await api.post<{ connection_id: string; status: string; message: string }>(
      `/connections/${connectionId}/test`
    );
    return response.data;
  },

  /**
   * Delete connection
   */
  async deleteConnection(connectionId: string): Promise<{ message: string; connection_id: string }> {
    const response = await api.delete<{ message: string; connection_id: string }>(`/connections/${connectionId}`);
    return response.data;
  },

  /**
   * Get collections/indexes for a connection
   */
  async getConnectionCollections(connectionId: string): Promise<ConnectionCollectionsResponse> {
    const response = await api.get<ConnectionCollectionsResponse>(`/connections/${connectionId}/collections`);
    return response.data;
  },

  // Ingestion pipeline methods
  /**
   * List raw documents
   */
  async getRawDocuments(params?: {
    status?: string;
    origin_source_type?: string;
    origin_source_id?: string;
    limit?: number;
    skip?: number;
  }, mongodbUri?: string): Promise<{ raw_documents: any[]; count: number }> {
    const headers: Record<string, string> = {};
    // Only add header if mongodbUri is provided and not empty
    if (mongodbUri && mongodbUri.trim()) {
      headers['X-MongoDB-URI'] = mongodbUri.trim();
    }
    const response = await api.get<{ raw_documents: any[]; count: number }>('/ingest/raw', { params, headers });
    return response.data;
  },

  /**
   * Get a raw document
   */
  async getRawDocument(rawDocumentId: string): Promise<any> {
    const response = await api.get<any>(`/ingest/raw/${rawDocumentId}`);
    return response.data;
  },

  /**
   * Process raw documents into vector data
   */
  async processRawDocuments(rawDocumentIds: string[], targetCollection?: string): Promise<any> {
    const response = await api.post<any>('/ingest/process', {
      raw_document_ids: rawDocumentIds,
      target_collection: targetCollection
    });
    return response.data;
  },

  /**
   * Ingest document from origin source
   */
  async ingestFromOrigin(data: {
    origin_source_type: string;
    origin_id: string;
    origin_source_id?: string;
    connection_config: any;
    skip_duplicates?: boolean;
  }, mongodbUri?: string): Promise<{ raw_document_id: string; status: string; reason?: string }> {
    const headers: Record<string, string> = {};
    if (mongodbUri) {
      headers['X-MongoDB-URI'] = mongodbUri;
    }
    const response = await api.post<{ raw_document_id: string; status: string }>('/ingest/origin', data, { headers });
    return response.data;
  },

  /**
   * Get ingestion status
   */
  async getIngestionStatus(): Promise<{ status_counts: Record<string, number>; total: number }> {
    const response = await api.get<{ status_counts: Record<string, number>; total: number }>('/ingest/status');
    return response.data;
  },

  /**
   * Delete raw document
   */
  async deleteRawDocument(rawDocumentId: string): Promise<{ message: string; raw_document_id: string }> {
    const response = await api.delete<{ message: string; raw_document_id: string }>(`/ingest/raw/${rawDocumentId}`);
    return response.data;
  },

  // Origin source methods
  /**
   * List available origin source types
   */
  async getOriginSourceTypes(): Promise<any[]> {
    const response = await api.get<{ source_types: any[] }>('/origin/sources');
    return response.data.source_types;
  },

  /**
   * Test connection to origin source
   */
  async testOriginConnection(sourceType: string, connectionConfig: any): Promise<{ status: string; message: string }> {
    const response = await api.post<{ status: string; message: string }>('/origin/connect', {
      source_type: sourceType,
      connection_config: connectionConfig
    });
    return response.data;
  },

  /**
   * List documents from origin source
   */
  async listOriginDocuments(sourceType: string, connectionConfig: any, limit?: number, skip?: number): Promise<any> {
    const response = await api.post<any>(`/origin/${sourceType}/documents`, {
      connection_config: connectionConfig,
      limit,
      skip
    });
    return response.data;
  },

  /**
   * Get document from origin source
   */
  async getOriginDocument(sourceType: string, originId: string, connectionConfig: any): Promise<any> {
    const response = await api.post<any>(`/origin/${sourceType}/documents/${originId}`, {
      connection_config: connectionConfig
    });
    return response.data;
  },
};

