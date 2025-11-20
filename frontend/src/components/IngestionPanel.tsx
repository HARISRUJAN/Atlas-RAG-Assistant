import React, { useState, useEffect } from 'react';
import { apiService } from '../api';
import { OriginSelector } from './OriginSelector';
import { RawDocumentList } from './RawDocumentList';
import { DatabaseCollectionSelector } from './DatabaseCollectionSelector';

interface IngestionPanelProps {
  mongodbUri?: string;
  connectionId?: string | null;
}

export const IngestionPanel: React.FC<IngestionPanelProps> = ({ 
  mongodbUri = '', 
  connectionId = null 
}) => {
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [targetCollection, setTargetCollection] = useState<string>('srugenai_db.movies');
  const [originSource, setOriginSource] = useState<string>('sample_mflix.movies');
  const [processing, setProcessing] = useState(false);
  const [originDocuments, setOriginDocuments] = useState<any[]>([]);
  const [selectedOriginDocs, setSelectedOriginDocs] = useState<Set<string>>(new Set());
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [activeTab, setActiveTab] = useState<'upload' | 'origin'>('upload');
  const [pipelineConfig, setPipelineConfig] = useState<{
    origin: string;
    target: string;
    status: string;
  } | null>(null);
  const [originConnectionStatus, setOriginConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected');
  const [loadingOriginDocuments, setLoadingOriginDocuments] = useState(false);
  const [ingestingDocuments, setIngestingDocuments] = useState(false);
  const [originConnectionError, setOriginConnectionError] = useState<string | null>(null);

  const handleProcessSelected = async () => {
    if (selectedDocumentIds.length === 0) {
      alert('Please select documents to process');
      return;
    }

    setProcessing(true);
    try {
      const result = await apiService.processRawDocuments(
        selectedDocumentIds,
        targetCollection || undefined
      );
      
      alert(`Processed ${result.successful || result.chunks_stored || 0} document(s) successfully`);
      setSelectedDocumentIds([]);
      setRefreshTrigger(prev => prev + 1);
    } catch (err: any) {
      alert(`Failed to process documents: ${err.message}`);
    } finally {
      setProcessing(false);
    }
  };

  // Parse originSource (e.g., "sample_mflix.movies") to extract database and collection
  const parseOriginSource = (source: string): { database: string; collection: string } | null => {
    if (!source || !source.includes('.')) {
      return null;
    }
    const parts = source.split('.');
    if (parts.length !== 2) {
      return null;
    }
    return {
      database: parts[0].trim(),
      collection: parts[1].trim()
    };
  };

  // Connect to origin and load documents
  const handleConnectAndLoadOrigin = async () => {
    if (!originSource) {
      alert('Please select an origin source first');
      return;
    }

    const parsed = parseOriginSource(originSource);
    if (!parsed) {
      alert('Invalid origin source format. Please use "database.collection" format (e.g., sample_mflix.movies)');
      return;
    }

    const currentMongoUri = mongodbUri || localStorage.getItem('mongodb_uri') || '';
    if (!currentMongoUri) {
      alert('MongoDB URI is required. Please configure it in the connection settings.');
      return;
    }

    setOriginConnectionStatus('connecting');
    setOriginConnectionError(null);
    setLoadingOriginDocuments(true);

    try {
      // Build MongoDB connection config
      const connectionConfig = {
        uri: currentMongoUri,
        database_name: parsed.database,
        collection_name: parsed.collection
      };

      // Test connection
      const testResult = await apiService.testOriginConnection('mongodb', connectionConfig);
      
      if (testResult.status !== 'connected') {
        setOriginConnectionStatus('error');
        setOriginConnectionError(testResult.message || 'Connection failed');
        alert(`Connection failed: ${testResult.message}`);
        return;
      }

      setOriginConnectionStatus('connected');

      // Load documents
      const result = await apiService.listOriginDocuments('mongodb', connectionConfig, 100, 0);
      console.log('[IngestionPanel] Load documents result:', result);
      console.log('[IngestionPanel] Result type:', typeof result);
      console.log('[IngestionPanel] Result keys:', Object.keys(result || {}));
      
      // Handle different possible response structures
      let docs = [];
      if (Array.isArray(result)) {
        docs = result;
      } else if (result && Array.isArray(result.documents)) {
        docs = result.documents;
      } else if (result && result.data && Array.isArray(result.data.documents)) {
        docs = result.data.documents;
      } else {
        console.error('[IngestionPanel] Unexpected response structure:', result);
      }
      
      console.log('[IngestionPanel] Parsed documents:', docs);
      console.log('[IngestionPanel] Document count:', docs.length);
      
      if (docs.length === 0) {
        setOriginConnectionError('No documents found in the selected origin source. Please check if the collection exists and has data.');
        setOriginDocuments([]);
        alert('No documents found in the selected origin source. Please check if the collection exists and has data.');
        return;
      }
      
      // Ensure all documents have origin_id
      const validDocs = docs.filter((doc: any) => doc && doc.origin_id);
      if (validDocs.length === 0) {
        console.error('[IngestionPanel] No valid documents with origin_id found');
        setOriginConnectionError('Documents loaded but missing required origin_id field.');
        setOriginDocuments([]);
        alert('Error: Documents loaded but missing required fields.');
        return;
      }
      
      setOriginDocuments(validDocs);
      handleOriginDocumentsLoaded(validDocs);
      setOriginConnectionError(null);
      
      alert(`Successfully loaded ${validDocs.length} document(s) from ${originSource}`);
    } catch (err: any) {
      setOriginConnectionStatus('error');
      const errorMessage = err.response?.data?.error || err.response?.data?.details || err.message || 'Failed to connect or load documents';
      const errorType = err.response?.data?.type || '';
      setOriginConnectionError(`${errorMessage}${errorType ? ` (${errorType})` : ''}`);
      
      console.error('[IngestionPanel] Error details:', {
        message: err.message,
        response: err.response?.data,
        status: err.response?.status
      });
      
      alert(`Error: ${errorMessage}${errorType ? ` (${errorType})` : ''}`);
    } finally {
      setLoadingOriginDocuments(false);
    }
  };

  // Ingest selected origin documents into raw_documents
  const handleIngestSelectedOriginDocs = async () => {
    if (selectedOriginDocs.size === 0) {
      alert('Please select documents to ingest');
      return;
    }

    const parsed = parseOriginSource(originSource);
    if (!parsed) {
      alert('Invalid origin source format. Please use "database.collection" format');
      return;
    }

    const currentMongoUri = mongodbUri || localStorage.getItem('mongodb_uri') || '';
    if (!currentMongoUri) {
      alert('MongoDB URI is required');
      return;
    }

    setIngestingDocuments(true);

    try {
      const connectionConfig = {
        uri: currentMongoUri,
        database_name: parsed.database,
        collection_name: parsed.collection
      };

      const selectedDocs = originDocuments.filter(doc => selectedOriginDocs.has(doc.origin_id));
      let successCount = 0;
      let errorCount = 0;

      for (const doc of selectedDocs) {
        try {
          await apiService.ingestFromOrigin({
            origin_source_type: 'mongodb',
            origin_id: doc.origin_id,
            connection_config: connectionConfig
          }, currentMongoUri);
          successCount++;
        } catch (err: any) {
          console.error(`Failed to ingest document ${doc.origin_id}:`, err);
          errorCount++;
        }
      }

      if (successCount > 0) {
        alert(`Successfully ingested ${successCount} document(s)${errorCount > 0 ? ` (${errorCount} failed)` : ''}`);
        setSelectedOriginDocs(new Set());
        setOriginDocuments([]);
        setRefreshTrigger(prev => prev + 1);
      } else {
        alert(`Failed to ingest documents: ${errorCount} error(s)`);
      }
    } catch (err: any) {
      alert(`Error ingesting documents: ${err.message}`);
    } finally {
      setIngestingDocuments(false);
    }
  };

  const handleOriginDocumentsLoaded = (docs: any[]) => {
    setOriginDocuments(docs);
  };

  const handleOriginDocSelect = (originId: string) => {
    const newSelected = new Set(selectedOriginDocs);
    if (newSelected.has(originId)) {
      newSelected.delete(originId);
    } else {
      newSelected.add(originId);
    }
    setSelectedOriginDocs(newSelected);
  };

  // Load MongoDB URI from localStorage if not provided
  useEffect(() => {
    if (!mongodbUri) {
      const storedUri = localStorage.getItem('mongodb_uri');
      if (storedUri) {
        // Use stored URI via parent component
      }
    }
  }, [mongodbUri]);

  // Update pipeline config display
  useEffect(() => {
    if (originSource && targetCollection) {
      setPipelineConfig({
        origin: originSource,
        target: targetCollection,
        status: 'configured'
      });
    }
  }, [originSource, targetCollection]);

  // Debug: Log when originDocuments changes
  useEffect(() => {
    console.log('[IngestionPanel] originDocuments state updated:', originDocuments.length, 'documents');
    if (originDocuments.length > 0) {
      console.log('[IngestionPanel] First document:', originDocuments[0]);
    }
  }, [originDocuments]);

  return (
    <div className="ingestion-panel p-6">
      <h2 className="text-2xl font-bold mb-6">Data Ingestion Pipeline</h2>

      {/* Pipeline Configuration Display */}
      {pipelineConfig && (
        <div className="mb-6 p-4 bg-gradient-to-r from-blue-50 to-green-50 border border-blue-200 rounded-lg">
          <h3 className="font-semibold mb-3 text-lg">Pipeline Configuration</h3>
          <div className="flex items-center gap-4 text-sm">
            <div className="flex-1">
              <div className="text-gray-600 mb-1">Origin Source:</div>
              <div className="font-mono font-semibold text-blue-700">{pipelineConfig.origin}</div>
            </div>
            <div className="text-gray-400">→</div>
            <div className="flex-1">
              <div className="text-gray-600 mb-1">Target Vector DB:</div>
              <div className="font-mono font-semibold text-green-700">{pipelineConfig.target}</div>
            </div>
            <div className="text-gray-400">→</div>
            <div className="flex-1">
              <div className="text-gray-600 mb-1">RAG Retrieval:</div>
              <div className="font-mono font-semibold text-purple-700">{pipelineConfig.target}</div>
            </div>
          </div>
          <div className="mt-3 text-xs text-gray-500">
            Data flows: Origin → raw_documents → Vector DB → RAG Queries
          </div>
        </div>
      )}

      <div className="mb-4 border-b">
        <button
          onClick={() => setActiveTab('upload')}
          className={`px-4 py-2 ${activeTab === 'upload' ? 'border-b-2 border-blue-500 font-semibold' : ''}`}
        >
          File Upload
        </button>
        <button
          onClick={() => setActiveTab('origin')}
          className={`px-4 py-2 ${activeTab === 'origin' ? 'border-b-2 border-blue-500 font-semibold' : ''}`}
        >
          Origin Source
        </button>
      </div>

      {activeTab === 'upload' && (
        <div className="space-y-6">
          {/* Target Vector Database Selection */}
          <div className="p-4 bg-white border border-gray-200 rounded-lg">
            <h3 className="font-semibold mb-3 text-lg">Target Vector Database</h3>
            <p className="text-sm text-gray-600 mb-3">
              Select where processed chunks will be stored (e.g., srugenai_db.movies)
            </p>
            <DatabaseCollectionSelector
              label="Target Vector Database"
              value={targetCollection}
              onChange={setTargetCollection}
              mongodbUri={mongodbUri || localStorage.getItem('mongodb_uri') || ''}
              connectionId={connectionId}
              placeholder="srugenai_db.movies"
              required={true}
            />
          </div>

          <RawDocumentList
            onSelectionChange={setSelectedDocumentIds}
            refreshTrigger={refreshTrigger}
            mongodbUri={mongodbUri || localStorage.getItem('mongodb_uri') || ''}
          />

          {selectedDocumentIds.length > 0 && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded">
              <h4 className="font-semibold mb-3">Process Selected Documents</h4>
              <div className="mb-3 p-3 bg-white rounded border">
                <div className="text-sm text-gray-600 mb-1">Target:</div>
                <div className="font-mono font-semibold">{targetCollection || 'default vector_data'}</div>
              </div>
              <button
                onClick={handleProcessSelected}
                disabled={processing || !targetCollection}
                className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
              >
                {processing ? 'Processing...' : `Process ${selectedDocumentIds.length} Document(s) → ${targetCollection}`}
              </button>
            </div>
          )}
        </div>
      )}

      {activeTab === 'origin' && (
        <div className="space-y-6">
          {/* Origin Source Selection */}
          <div className="p-4 bg-white border border-gray-200 rounded-lg">
            <h3 className="font-semibold mb-3 text-lg">Origin Source</h3>
            <p className="text-sm text-gray-600 mb-3">
              Select the source database/collection where data originates (e.g., sample_mflix.movies)
            </p>
            <DatabaseCollectionSelector
              label="Origin Source Database"
              value={originSource}
              onChange={setOriginSource}
              mongodbUri={mongodbUri || localStorage.getItem('mongodb_uri') || ''}
              connectionId={connectionId}
              placeholder="sample_mflix.movies"
              required={true}
            />
          </div>

          {/* Target Vector Database Selection for Origin Tab */}
          <div className="p-4 bg-white border border-gray-200 rounded-lg">
            <h3 className="font-semibold mb-3 text-lg">Target Vector Database</h3>
            <p className="text-sm text-gray-600 mb-3">
              Select where processed chunks will be stored (e.g., srugenai_db.movies)
            </p>
            <DatabaseCollectionSelector
              label="Target Vector Database"
              value={targetCollection}
              onChange={setTargetCollection}
              mongodbUri={mongodbUri || localStorage.getItem('mongodb_uri') || ''}
              connectionId={connectionId}
              placeholder="srugenai_db.movies"
              required={true}
            />
          </div>

          {/* Connect & Load Documents Button */}
          <div className="p-4 bg-white border border-gray-200 rounded-lg">
            <h3 className="font-semibold mb-3 text-lg">Connect to Origin Source</h3>
            <p className="text-sm text-gray-600 mb-3">
              Connect to the selected origin source and load documents for ingestion
            </p>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <button
                  onClick={handleConnectAndLoadOrigin}
                  disabled={!originSource || loadingOriginDocuments || originConnectionStatus === 'connecting'}
                  className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loadingOriginDocuments ? 'Connecting & Loading...' : originConnectionStatus === 'connected' ? 'Reload Documents' : 'Connect & Load Documents'}
                </button>
                {originConnectionStatus === 'connected' && (
                  <span className="text-sm text-green-600 font-semibold">✓ Connected</span>
                )}
                {originConnectionStatus === 'error' && (
                  <span className="text-sm text-red-600 font-semibold">✗ Connection Failed</span>
                )}
              </div>
              {originConnectionError && (
                <div className="p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                  {originConnectionError}
                </div>
              )}
              {originConnectionStatus === 'connected' && (
                <div className={`text-sm ${originDocuments.length > 0 ? 'text-green-600' : 'text-yellow-600'}`}>
                  {originDocuments.length > 0 
                    ? `✓ Loaded ${originDocuments.length} document(s) from ${originSource}`
                    : `⚠ Connected but no documents found in ${originSource}`}
                </div>
              )}
            </div>
          </div>

          {/* Optional: Keep OriginSelector for manual configuration if needed */}
          <details className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
            <summary className="cursor-pointer text-sm text-gray-600 font-medium">
              Advanced: Manual Origin Configuration
            </summary>
            <div className="mt-3">
              <OriginSelector
                onSelect={(_sourceType, _connectionConfig) => {
                  // This will be called when user wants to ingest
                }}
                onDocumentsLoaded={handleOriginDocumentsLoaded}
              />
            </div>
          </details>

          {/* Debug info - show even when empty to help diagnose */}
          {import.meta.env.DEV && (
            <div className="p-2 bg-gray-100 text-xs text-gray-600 rounded">
              Debug: originDocuments.length = {originDocuments.length}, 
              originConnectionStatus = {originConnectionStatus}
              {originDocuments.length > 0 && `, first doc: ${JSON.stringify(originDocuments[0]).substring(0, 100)}`}
            </div>
          )}

          {originDocuments.length > 0 && (
            <div className="mt-6">
              <h4 className="font-semibold mb-3">Select Documents to Ingest ({originDocuments.length} available)</h4>
              <div className="space-y-2 max-h-64 overflow-y-auto border rounded p-3">
                {originDocuments.map((doc, index) => {
                  const docKey = doc.origin_id || `doc-${index}`;
                  return (
                    <div
                      key={docKey}
                      className={`p-2 border rounded flex items-center gap-2 ${
                        selectedOriginDocs.has(doc.origin_id) ? 'bg-blue-50 border-blue-300' : ''
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedOriginDocs.has(doc.origin_id)}
                        onChange={() => handleOriginDocSelect(doc.origin_id)}
                      />
                      <div className="flex-1">
                        <div className="font-medium">{doc.title || doc.origin_id || `Document ${index + 1}`}</div>
                        {doc.content_preview && (
                          <div className="text-sm text-gray-600 truncate">
                            {doc.content_preview}
                          </div>
                        )}
                        {!doc.content_preview && doc.origin_id && (
                          <div className="text-xs text-gray-400">
                            ID: {doc.origin_id}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
              
              {selectedOriginDocs.size > 0 && (
                <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded">
                  <h4 className="font-semibold mb-3">Ingest Selected Documents</h4>
                  <div className="mb-3 p-3 bg-white rounded border">
                    <div className="text-sm text-gray-600 mb-1">Origin:</div>
                    <div className="font-mono font-semibold text-blue-700">{originSource}</div>
                    <div className="text-sm text-gray-600 mb-1 mt-2">Target:</div>
                    <div className="font-mono font-semibold text-green-700">{targetCollection || 'default vector_data'}</div>
                  </div>
                  <button
                    onClick={handleIngestSelectedOriginDocs}
                    disabled={ingestingDocuments || originConnectionStatus !== 'connected'}
                    className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {ingestingDocuments 
                      ? `Ingesting ${selectedOriginDocs.size} Document(s)...` 
                      : `Ingest ${selectedOriginDocs.size} Document(s) → raw_documents`}
                  </button>
                  {originConnectionStatus !== 'connected' && (
                    <p className="mt-2 text-sm text-red-600">
                      Please connect to origin source first
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

