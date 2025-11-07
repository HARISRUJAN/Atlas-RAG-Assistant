/**
 * API service for communicating with the Flask backend
 */

import axios from 'axios';
import type { QueryResponse, UploadResponse, HealthStatus } from './types';

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
  async query(query: string, topK: number = 5): Promise<QueryResponse> {
    const response = await api.post<QueryResponse>('/query', {
      query,
      top_k: topK,
    });
    
    return response.data;
  },

  /**
   * Check system health
   */
  async healthCheck(): Promise<HealthStatus> {
    const response = await api.get<HealthStatus>('/health');
    return response.data;
  },
};

