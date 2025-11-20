import React, { useState, useEffect } from 'react';
import { apiService } from '../api';
import { DatabaseCollectionSelector } from './DatabaseCollectionSelector';
import { RawDocumentList } from './RawDocumentList';

interface IngestionPipelinePanelProps {
  mongodbUri?: string;
  connectionId?: string | null;
}

export const IngestionPipelinePanel: React.FC<IngestionPipelinePanelProps> = ({
  mongodbUri = '',
  connectionId = null
}) => {
  const [originSource, setOriginSource] = useState<string>('sample_mflix.movies');
  const [targetCollection, setTargetCollection] = useState<string>('srugenai_db.movies');
  const [originDocuments, setOriginDocuments] = useState<any[]>([]);
  const [selectedOriginDocs, setSelectedOriginDocs] = useState<Set<string>>(new Set());
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [loadingOriginDocuments, setLoadingOriginDocuments] = useState(false);
  const [ingestingDocuments, setIngestingDocuments] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [status, setStatus] = useState<string>('');
  const [refreshTrigger, setRefreshTrigger] = useState(0);

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
  const handleLoad = async () => {
    if (!originSource) {
      setStatus('Please select an origin source first');
      return;
    }

    const parsed = parseOriginSource(originSource);
    if (!parsed) {
      setStatus('Invalid origin source format. Please use "database.collection" format (e.g., sample_mflix.movies)');
      return;
    }

    const currentMongoUri = mongodbUri || localStorage.getItem('mongodb_uri') || '';
    if (!currentMongoUri) {
      setStatus('MongoDB URI is required. Please configure it in the connection settings.');
      return;
    }

    setLoadingOriginDocuments(true);
    setStatus('Loading documents...');

    try {
      const connectionConfig = {
        uri: currentMongoUri,
        database_name: parsed.database,
        collection_name: parsed.collection
      };

      // Test connection
      const testResult = await apiService.testOriginConnection('mongodb', connectionConfig);
      
      if (testResult.status !== 'connected') {
        setStatus(`Connection failed: ${testResult.message}`);
        return;
      }

      // Load documents
      const result = await apiService.listOriginDocuments('mongodb', connectionConfig, 100, 0);
      const docs = result.documents || [];
      
      if (docs.length === 0) {
        setStatus('No documents found in the selected origin source.');
        setOriginDocuments([]);
        return;
      }
      
      setOriginDocuments(docs);
      setStatus(`${docs.length} document(s) loaded and ready to process.`);
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.response?.data?.details || err.message || 'Failed to load documents';
      setStatus(`Error: ${errorMessage}`);
    } finally {
      setLoadingOriginDocuments(false);
    }
  };

  // Ingest selected origin documents into raw_documents
  const handleIngest = async () => {
    if (selectedOriginDocs.size === 0) {
      setStatus('Please select documents to ingest');
      return;
    }

    const parsed = parseOriginSource(originSource);
    if (!parsed) {
      setStatus('Invalid origin source format');
      return;
    }

    const currentMongoUri = mongodbUri || localStorage.getItem('mongodb_uri') || '';
    if (!currentMongoUri) {
      setStatus('MongoDB URI is required');
      return;
    }

    setIngestingDocuments(true);
    setStatus('Ingesting documents...');

    try {
      const connectionConfig = {
        uri: currentMongoUri,
        database_name: parsed.database,
        collection_name: parsed.collection
      };

      const selectedDocs = originDocuments.filter(doc => selectedOriginDocs.has(doc.origin_id));
      let successCount = 0;
      let errorCount = 0;

      let skippedCount = 0;
      for (const doc of selectedDocs) {
        try {
          const result = await apiService.ingestFromOrigin({
            origin_source_type: 'mongodb',
            origin_id: doc.origin_id,
            connection_config: connectionConfig,
            skip_duplicates: true
          }, currentMongoUri);
          
          if (result.status === 'skipped') {
            skippedCount++;
          } else {
            successCount++;
          }
        } catch (err: any) {
          console.error(`Failed to ingest document ${doc.origin_id}:`, err);
          errorCount++;
        }
      }

      if (successCount > 0 || skippedCount > 0) {
        const parts = [];
        if (successCount > 0) parts.push(`${successCount} ingested`);
        if (skippedCount > 0) parts.push(`${skippedCount} skipped (already ingested)`);
        if (errorCount > 0) parts.push(`${errorCount} failed`);
        setStatus(`Ingestion complete: ${parts.join(', ')}`);
        setSelectedOriginDocs(new Set());
        setOriginDocuments([]);
        setRefreshTrigger(prev => prev + 1);
      } else {
        setStatus(`Failed to ingest documents: ${errorCount} error(s)`);
      }
    } catch (err: any) {
      setStatus(`Error ingesting documents: ${err.message}`);
    } finally {
      setIngestingDocuments(false);
    }
  };

  // Process raw documents to vector collection
  const handleProcess = async () => {
    if (selectedDocumentIds.length === 0) {
      setStatus('⚠️ Please select raw documents to process');
      return;
    }

    if (!targetCollection) {
      setStatus('⚠️ Please select a target vector collection');
      return;
    }

    setProcessing(true);
    setStatus(`🔄 Processing ${selectedDocumentIds.length} document(s)...\nStep 1: Semantic Chunking → Step 2: Vector Embeddings → Step 3: Storing in ${targetCollection}`);

    try {
      const result = await apiService.processRawDocuments(
        selectedDocumentIds,
        targetCollection || undefined
      );
      
      const successful = result.successful || result.processed_count || 0;
      const chunksStored = result.chunks_stored || result.total_chunks_stored || 0;
      
      setStatus(`✅ Successfully processed ${successful} document(s)!\n📊 Created ${chunksStored} vector chunks with embeddings\n💾 Stored in: ${targetCollection}`);
      setSelectedDocumentIds([]);
      setRefreshTrigger(prev => prev + 1);
    } catch (err: any) {
      setStatus(`❌ Failed to process documents: ${err.response?.data?.error || err.message}\n\nPlease check:\n- Target collection exists\n- Vector index is created\n- MongoDB connection is valid`);
    } finally {
      setProcessing(false);
    }
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

  const currentMongoUri = mongodbUri || localStorage.getItem('mongodb_uri') || '';

  return (
    <div className="ingestion-pipeline-panel space-y-4">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-mongodb-darkGray mb-2">Data Ingestion Pipeline</h3>
        <div className="text-xs text-gray-600 bg-blue-50 p-2 rounded">
          <div className="font-semibold mb-1">Pipeline Flow:</div>
          <div>1. Load from Origin → 2. Ingest to Raw → 3. Process (Chunk + Embed) → 4. Store in Vector DB</div>
        </div>
      </div>
      
      {/* Step 1: Origin Source Selection */}
      <div className="space-y-2 border-b pb-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold">1</span>
          <label className="block text-sm font-medium text-mongodb-darkGray">
            Load from Origin Source
          </label>
        </div>
        <DatabaseCollectionSelector
          label=""
          value={originSource}
          onChange={setOriginSource}
          mongodbUri={currentMongoUri}
          connectionId={connectionId}
          placeholder="sample_mflix.movies"
          required={true}
        />
        <button
          onClick={handleLoad}
          disabled={!originSource || loadingOriginDocuments}
          className="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
        >
          {loadingOriginDocuments ? '⏳ Loading Documents...' : '📥 Load Documents from Origin'}
        </button>
      </div>

      {/* Step 1.5: Ingest to Raw Documents */}
      {originDocuments.length > 0 && (
        <div className="space-y-2 border-b pb-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="bg-green-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold">1.5</span>
            <label className="block text-sm font-medium text-mongodb-darkGray">
              Ingest to Raw Documents
            </label>
          </div>
          <div className="text-xs text-gray-600 mb-2">
            {originDocuments.length} document(s) loaded. Select documents to ingest into raw_documents:
          </div>
          <div className="max-h-48 overflow-y-auto border rounded p-2 space-y-1 bg-gray-50">
            {originDocuments.map((doc) => (
              <div
                key={doc.origin_id}
                className={`p-2 border rounded flex items-center gap-2 cursor-pointer transition-colors ${
                  selectedOriginDocs.has(doc.origin_id) ? 'bg-green-50 border-green-300' : 'bg-white hover:bg-gray-50'
                }`}
                onClick={() => handleOriginDocSelect(doc.origin_id)}
              >
                <input
                  type="checkbox"
                  checked={selectedOriginDocs.has(doc.origin_id)}
                  onChange={() => handleOriginDocSelect(doc.origin_id)}
                  onClick={(e) => e.stopPropagation()}
                  className="cursor-pointer"
                />
                <div className="flex-1 text-sm">
                  <div className="font-medium">{doc.title || doc.origin_id}</div>
                  {doc.content_preview && (
                    <div className="text-xs text-gray-500 truncate">
                      {doc.content_preview}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
          <button
            onClick={handleIngest}
            disabled={selectedOriginDocs.size === 0 || ingestingDocuments}
            className="w-full px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
          >
            {ingestingDocuments ? '⏳ Ingesting to raw_documents...' : `💾 Ingest ${selectedOriginDocs.size} Document(s) → raw_documents`}
          </button>
        </div>
      )}

      {/* Target Vector Collection */}
      <div className="space-y-2 border-b pb-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="bg-purple-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold">2</span>
          <label className="block text-sm font-medium text-mongodb-darkGray">
            Target Vector Collection
          </label>
        </div>
        <div className="text-xs text-gray-600 mb-2">
          Where processed chunks with embeddings will be stored:
        </div>
        <DatabaseCollectionSelector
          label=""
          value={targetCollection}
          onChange={setTargetCollection}
          mongodbUri={currentMongoUri}
          connectionId={connectionId}
          placeholder="srugenai_db.movies"
          required={true}
        />
      </div>

      {/* Processing Section - Most Important */}
      <div className="space-y-3 border-t pt-4 bg-gradient-to-r from-purple-50 to-blue-50 p-4 rounded-lg">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-base font-semibold text-mongodb-darkGray mb-1">
              Step 2: Process to Vector Collection
            </h4>
            <p className="text-xs text-gray-600">
              Select raw documents → Chunk & Embed → Store in {targetCollection || 'vector collection'}
            </p>
          </div>
        </div>
        
        <RawDocumentList
          onSelectionChange={setSelectedDocumentIds}
          refreshTrigger={refreshTrigger}
          mongodbUri={mongodbUri || localStorage.getItem('mongodb_uri') || ''}
        />
        
        {selectedDocumentIds.length > 0 ? (
          <div className="space-y-2">
            <div className="p-3 bg-white rounded border border-purple-200">
              <div className="text-sm font-medium text-purple-700 mb-1">
                Ready to Process
              </div>
              <div className="text-xs text-gray-600">
                {selectedDocumentIds.length} document(s) selected → Will be chunked → Embedded → Stored in <span className="font-mono font-semibold">{targetCollection || 'target collection'}</span>
              </div>
            </div>
            <button
              onClick={handleProcess}
              disabled={processing || !targetCollection}
              className="w-full px-4 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg hover:from-purple-700 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-semibold shadow-lg"
            >
              {processing ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Processing (Chunking → Embedding → Storing)...
                </span>
              ) : (
                `🚀 Process ${selectedDocumentIds.length} Document(s) → ${targetCollection || 'Vector Collection'}`
              )}
            </button>
          </div>
        ) : (
          <div className="p-3 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800">
            ⚠️ Select raw documents above to process them through semantic chunking and vector embeddings
          </div>
        )}
      </div>

      {/* Status */}
      {status && (
        <div className={`p-3 rounded-lg text-sm border-2 whitespace-pre-line ${
          status.includes('❌') || status.includes('Error') || status.includes('Failed') 
            ? 'bg-red-50 text-red-700 border-red-300' 
            : status.includes('✅') || status.includes('Success') || status.includes('Processed')
            ? 'bg-green-50 text-green-700 border-green-300'
            : status.includes('⚠️')
            ? 'bg-yellow-50 text-yellow-700 border-yellow-300'
            : 'bg-blue-50 text-blue-700 border-blue-300'
        }`}>
          <div className="font-semibold mb-1">Status:</div>
          <div>{status}</div>
        </div>
      )}
    </div>
  );
};

