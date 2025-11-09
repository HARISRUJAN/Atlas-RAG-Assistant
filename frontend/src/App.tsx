/**
 * Main application component
 */

import { useState, useEffect } from 'react';
import FileUpload from './components/FileUpload';
import QueryInput from './components/QueryInput';
import ResponseDisplay from './components/ResponseDisplay';
import CollectionSelector from './components/CollectionSelector';
import { apiService } from './api';
import type { QueryResponse, UploadResponse, HealthStatus, UploadedFile } from './types';

function App() {
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [isQueryLoading, setIsQueryLoading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [selectedCollection, setSelectedCollection] = useState<string | null>(null);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const [isLoadingQuestions, setIsLoadingQuestions] = useState(false);

  useEffect(() => {
    // Check health on mount
    checkHealth();
  }, []);

  useEffect(() => {
    // Fetch suggested questions when collection changes
    if (selectedCollection) {
      fetchSuggestedQuestions(selectedCollection);
    } else {
      setSuggestedQuestions([]);
    }
  }, [selectedCollection]);

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

  const fetchSuggestedQuestions = async (collectionName: string) => {
    setIsLoadingQuestions(true);
    try {
      const questions = await apiService.getSuggestedQuestions(collectionName);
      setSuggestedQuestions(questions);
    } catch (error: any) {
      console.error('Error fetching suggested questions:', error);
      // Set empty array on error, so no questions are shown
      setSuggestedQuestions([]);
    } finally {
      setIsLoadingQuestions(false);
    }
  };

  const handleCollectionChange = (collectionName: string | null) => {
    setSelectedCollection(collectionName);
    // Clear previous response when collection changes
    setResponse(null);
  };

  const handleQuery = async (query: string) => {
    setIsQueryLoading(true);
    try {
      // selectedCollection is now in format "database.collection" or just "collection"
      const queryResponse = await apiService.query(query, 5, selectedCollection || undefined);
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

      {/* Main Content - 3 Column Layout */}
      <main className="flex h-[calc(100vh-80px)] overflow-hidden">
        {/* Left Column: Collections Sidebar */}
        <div className="w-64 flex-shrink-0 border-r" style={{ borderColor: 'var(--color-border-muted)', backgroundColor: 'white' }}>
          <CollectionSelector
            selectedCollection={selectedCollection}
            onCollectionChange={handleCollectionChange}
          />
        </div>

        {/* Center Column: Chat Interface */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-6">
            <ResponseDisplay response={response} isLoading={isQueryLoading} />
          </div>
          <div className="border-t p-6" style={{ borderColor: 'var(--color-border-muted)', backgroundColor: 'white' }}>
            <QueryInput 
              onSubmit={handleQuery} 
              isLoading={isQueryLoading}
              suggestedQuestions={suggestedQuestions}
            />
          </div>
        </div>

        {/* Right Column: Upload & Match Panel */}
        <div className="w-80 flex-shrink-0 border-l overflow-y-auto" style={{ borderColor: 'var(--color-border-muted)', backgroundColor: 'white' }}>
          <div className="p-6 space-y-6">
            <FileUpload 
              onUploadSuccess={handleUploadSuccess}
              uploadedFiles={uploadedFiles}
              onFileSelectionToggle={handleFileSelectionToggle}
            />
            
            {/* Source References Section */}
            {response && response.sources && response.sources.length > 0 && (
              <div className="card">
                <h3 className="text-lg font-semibold text-mongodb-darkGray mb-4">
                  Source Matches ({response.sources.length})
                </h3>
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {response.sources.map((source, index) => (
                    <div key={index} className="p-3 border rounded" style={{ borderColor: 'var(--color-border-muted)' }}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium" style={{ color: 'var(--color-text-dark)' }}>
                          #{index + 1} {source.file_name}
                        </span>
                        <span className="text-xs px-2 py-1 rounded" style={{ 
                          backgroundColor: 'var(--color-accent-green)', 
                          color: 'white'
                        }}>
                          {Math.round(source.relevance_score * 100)}%
                        </span>
                      </div>
                      <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                        Lines {source.line_start}-{source.line_end}
                      </p>
                      <p className="text-xs mt-2 line-clamp-3" style={{ color: 'var(--color-text-muted)' }}>
                        {source.content}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
