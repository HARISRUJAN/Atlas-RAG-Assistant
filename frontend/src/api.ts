/**
 * API service for communicating with the Flask backend
 */

import axios from 'axios';
import type { QueryResponse, UploadResponse, HealthStatus, Database } from './types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const apiService = {
  /**
   * Upload a file for processing
   */
  async uploadFile(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post<UploadResponse>('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  },

  /**
   * Query the RAG system
   */
  async query(query: string, topK: number = 5, collectionName?: string): Promise<QueryResponse> {
    const response = await api.post<QueryResponse>('/query', {
      query,
      top_k: topK,
      collection_name: collectionName,
    });
    
    return response.data;
  },

  /**
   * Get list of all MongoDB databases with their collections
   */
  async getDatabases(): Promise<Database[]> {
    const response = await api.get<{ databases: Database[] }>('/collections');
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
  async getSuggestedQuestions(collectionName: string): Promise<string[]> {
    // URL encode the collection path in case it contains special characters
    const encodedPath = encodeURIComponent(collectionName);
    const response = await api.get<{ questions: string[] }>(`/collections/${encodedPath}/questions`);
    return response.data.questions;
  },

  /**
   * Check system health
   */
  async healthCheck(): Promise<HealthStatus> {
    const response = await api.get<HealthStatus>('/health');
    return response.data;
  },
};

