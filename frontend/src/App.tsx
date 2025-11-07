/**
 * Main application component
 */

import { useState, useEffect } from 'react';
import FileUpload from './components/FileUpload';
import QueryInput from './components/QueryInput';
import ResponseDisplay from './components/ResponseDisplay';
import { apiService } from './api';
import type { QueryResponse, UploadResponse, HealthStatus, UploadedFile } from './types';

function App() {
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [isQueryLoading, setIsQueryLoading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [health, setHealth] = useState<HealthStatus | null>(null);

  useEffect(() => {
    // Check health on mount
    checkHealth();
  }, []);

  const checkHealth = async () => {
    try {
      const healthStatus = await apiService.healthCheck();
      setHealth(healthStatus);
    } catch (error) {
      console.error('Health check failed:', error);
    }
  };

  const handleUploadSuccess = (uploadResponse: UploadResponse) => {
    const newFile: UploadedFile = {
      document_id: uploadResponse.document_id,
      file_name: uploadResponse.file_name,
      total_chunks: uploadResponse.total_chunks,
      stored_chunks: uploadResponse.stored_chunks,
      selectedForIndex: true,  // Auto-select newly uploaded files
      upload_date: new Date().toISOString()
    };
    setUploadedFiles(prev => [...prev, newFile]);
  };

  const handleFileSelectionToggle = (documentId: string) => {
    setUploadedFiles(prev => 
      prev.map(file => 
        file.document_id === documentId 
          ? { ...file, selectedForIndex: !file.selectedForIndex }
          : file
      )
    );
  };

  const handleQuery = async (query: string) => {
    setIsQueryLoading(true);
    try {
      const queryResponse = await apiService.query(query);
      setResponse(queryResponse);
    } catch (error: any) {
      console.error('Query failed:', error);
      setResponse({
        answer: `Error: ${error.response?.data?.error || error.message || 'Query failed'}`,
        sources: [],
        query: query
      });
    } finally {
      setIsQueryLoading(false);
    }
  };

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-bg-primary)' }}>
      {/* Header */}
      <header className="bg-white shadow-sm" style={{ borderBottom: '1px solid var(--color-border-muted)' }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-center gap-3">
            <svg
              className="h-10 w-10"
              style={{ color: 'var(--color-accent-green)' }}
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path d="M17.193 9.555c-1.264-5.58-4.252-7.414-4.573-8.115-.28-.394-.53-.954-.735-1.44-.036.495-.055.685-.523 1.184-.723.566-4.438 3.682-4.74 10.02-.282 5.912 4.27 9.435 4.888 9.884l.07.05A73.49 73.49 0 0111.91 24h.481c.114-1.032.284-2.056.51-3.07.417-.296 4.604-3.254 4.293-11.375z" />
            </svg>
            <h1 className="text-3xl font-bold" style={{ color: 'var(--color-text-dark)' }}>
              MongoDB RAG System
            </h1>
            
            {/* Health Status */}
            {health && (
              <div className="flex items-center space-x-2 ml-4">
                <div 
                  className="h-3 w-3 rounded-full"
                  style={{ 
                    backgroundColor: health.status === 'healthy' 
                      ? 'var(--color-accent-green)' 
                      : '#FFA500'
                  }}
                ></div>
                <span className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                  {health.status === 'healthy' ? 'System Ready' : 'System Degraded'}
                </span>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column: Upload and Query */}
          <div className="space-y-6">
            <FileUpload 
              onUploadSuccess={handleUploadSuccess}
              uploadedFiles={uploadedFiles}
              onFileSelectionToggle={handleFileSelectionToggle}
            />
            
            <QueryInput onSubmit={handleQuery} isLoading={isQueryLoading} />
          </div>

          {/* Right Column: Response */}
          <div>
            <ResponseDisplay response={response} isLoading={isQueryLoading} />
          </div>
        </div>

        {/* Footer Info */}
        <div className="mt-12 text-center">
          <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
            Powered by MongoDB Atlas Vector Search, LangChain, and Llama 3.2
          </p>
        </div>
      </main>
    </div>
  );
}

export default App;
