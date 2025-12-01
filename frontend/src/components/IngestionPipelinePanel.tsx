import React, { useState } from 'react';
import { apiService } from '../api';
import { DatabaseCollectionSelector } from './DatabaseCollectionSelector';

interface IngestionPipelinePanelProps {
  mongodbUri?: string;
  connectionId?: string | null;
}

export const IngestionPipelinePanel: React.FC<IngestionPipelinePanelProps> = ({
  mongodbUri = '',
  connectionId = null
}) => {
  const [originSource, setOriginSource] = useState<string>('srugenai_db.movies');
  const [ingestingDocuments, setIngestingDocuments] = useState(false);
  const [status, setStatus] = useState<string>('');
  const [ingestionProgress, setIngestionProgress] = useState<{
    current: number;
    total: number;
    successful: number;
    skipped: number;
    failed: number;
  } | null>(null);

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

  // Ingest all documents directly from MongoDB origin to semantic collection (automated ingestion)
  const handleIngestAllFromMongoDB = async () => {
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

    setIngestingDocuments(true);
    setIngestionProgress({ current: 0, total: 1, successful: 0, skipped: 0, failed: 0 });
    setStatus('🔄 Starting ingestion from origin to semantic collection...');

    try {
      const result = await apiService.ingestFromMongoDBOrigin({
        database_name: parsed.database,
        collection_name: parsed.collection,
        mode: 'all',
        skip_duplicates: true
      }, currentMongoUri);

      const { total, successful, skipped, failed, semantic_collection, details } = result;

      setIngestionProgress({
        current: total,
        total: total,
        successful: successful || 0,
        skipped: skipped || 0,
        failed: failed || 0,
      });

      const parts = [];
      if (successful > 0) parts.push(`✅ ${successful} ingested`);
      if (skipped > 0) parts.push(`⚠️ ${skipped} skipped (already indexed)`);
      if (failed > 0) parts.push(`❌ ${failed} failed`);

      let statusMessage = `Ingestion to ${semantic_collection || semanticCollectionName} complete:\n${parts.join(', ')}`;

      if (details && details.length > 0) {
        const totalChunks = details.reduce((sum: number, d: any) => sum + (d.total_chunks || 0), 0);
        if (totalChunks > 0) {
          statusMessage += `\n\nTotal chunks created: ${totalChunks}`;
        }

        if (failed > 0) {
          const failedDocs = details.filter((d: any) => d.status === 'failed');
          if (failedDocs.length > 0) {
            statusMessage += `\n\nFailed documents:\n${failedDocs.map((d: any) => `  - ${d.origin_id}: ${d.error || 'Unknown error'}`).join('\n')}`;
          }
        }
      }

      setStatus(statusMessage);
      
      // Trigger collections refresh after successful ingestion
      if (successful > 0 || skipped > 0) {
        // Dispatch custom event to trigger collections refresh
        window.dispatchEvent(new CustomEvent('collections-refresh'));
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.response?.data?.details || err.message || 'Failed to ingest documents';
      setStatus(`❌ Error ingesting from MongoDB origin: ${errorMessage}`);
      setIngestionProgress(null);
    } finally {
      setIngestingDocuments(false);
      setTimeout(() => {
        setIngestionProgress(null);
      }, 5000);
    }
  };

  const currentMongoUri = mongodbUri || localStorage.getItem('mongodb_uri') || '';

  // Calculate semantic collection name from origin source
  // This matches the backend Config.get_semantic_collection_name() logic
  const getSemanticCollectionName = (originSource: string): string => {
    if (!originSource) {
      return '';
    }
    
    // Handle "database.collection" format
    if (originSource.includes('.')) {
      const parts = originSource.split('.');
      if (parts.length === 2) {
        const [dbName, collName] = parts;
        // Prevent double suffix
        if (collName.endsWith('_semantic')) {
          return originSource;
        }
        return `${dbName}.${collName}_semantic`;
      }
    }
    
    // Single collection name
    // Prevent double suffix
    if (originSource.endsWith('_semantic')) {
      return originSource;
    }
    return `${originSource}_semantic`;
  };

  const semanticCollectionName = getSemanticCollectionName(originSource);

  return (
    <div className="ingestion-pipeline-panel space-y-4">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-mongodb-darkGray mb-2">Automated Data Ingestion</h3>
        {originSource && (
          <div className="text-xs text-gray-600 bg-blue-100 border-l-4 border-blue-500 text-blue-700 p-3 rounded-md mb-2">
            <p className="font-semibold mb-1">Architecture:</p>
            <p>Origin Collection: <span className="font-mono">{originSource}</span> (Your raw data)</p>
            <p>Semantic Collection: <span className="font-mono">{semanticCollectionName}</span> (Vector embeddings for RAG)</p>
            <p className="mt-2">RAG queries will ONLY use the Semantic Collection.</p>
          </div>
        )}
      </div>
      
      {/* Origin Source Selection and Ingest Button */}
      <div className="space-y-3 border-b pb-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold">1</span>
          <label className="block text-sm font-medium text-mongodb-darkGray">
            Select Origin Source
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
          onClick={handleIngestAllFromMongoDB}
          disabled={!originSource || ingestingDocuments}
          className="w-full px-4 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg hover:from-green-700 hover:to-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed font-semibold shadow-lg flex items-center justify-center gap-2"
          title="Ingest all documents directly from MongoDB origin to semantic collection"
        >
          {ingestingDocuments ? (
            <>
              <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span>Ingesting...</span>
            </>
          ) : (
            <>
              <span>🚀</span>
              <span>Ingest All → Semantic Collection</span>
            </>
          )}
        </button>

        {/* Progress indicator */}
        {ingestionProgress && (
          <div className="bg-gray-50 border rounded-lg p-3">
            <div className="flex items-center justify-between text-sm mb-2">
              <span className="font-medium">Progress:</span>
              <span>{ingestionProgress.current} / {ingestionProgress.total}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3 mb-2">
              <div 
                className="bg-gradient-to-r from-green-500 to-blue-500 h-3 rounded-full transition-all duration-300"
                style={{ width: `${(ingestionProgress.current / ingestionProgress.total) * 100}%` }}
              ></div>
            </div>
            <div className="flex gap-4 text-xs text-gray-600">
              {ingestionProgress.successful > 0 && <span className="flex items-center gap-1">✅ {ingestionProgress.successful} successful</span>}
              {ingestionProgress.skipped > 0 && <span className="flex items-center gap-1">⚠️ {ingestionProgress.skipped} skipped</span>}
              {ingestionProgress.failed > 0 && <span className="flex items-center gap-1">❌ {ingestionProgress.failed} failed</span>}
            </div>
          </div>
        )}
      </div>

      {/* Status */}
      {status && (
        <div className={`p-3 rounded-lg text-sm border-2 whitespace-pre-line ${
          status.includes('❌') || status.includes('Error') || status.includes('Failed') 
            ? 'bg-red-50 text-red-700 border-red-300' 
            : status.includes('✅') || status.includes('Success') || status.includes('Processed') || status.includes('complete')
            ? 'bg-green-50 text-green-700 border-green-300'
            : status.includes('⚠️') || status.includes('skipped') || status.includes('duplicate')
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

