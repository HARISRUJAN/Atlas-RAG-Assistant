import React, { useState, useEffect } from 'react';
import { apiService } from '../api';

interface RawDocument {
  raw_document_id: string;
  origin_id: string;
  origin_source_type: string;
  origin_source_id?: string;
  raw_content: string;
  content_type: string;
  metadata: any;
  status: 'pending' | 'processing' | 'processed' | 'failed';
  created_at: string;
  processed_at?: string;
  error_message?: string;
}

interface RawDocumentListProps {
  onSelectionChange: (selectedIds: string[]) => void;
  refreshTrigger?: number;
  mongodbUri?: string;
}

export const RawDocumentList: React.FC<RawDocumentListProps> = ({ onSelectionChange, refreshTrigger, mongodbUri }) => {
  const [documents, setDocuments] = useState<RawDocument[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');

  useEffect(() => {
    loadDocuments();
  }, [statusFilter, refreshTrigger]);

  const loadDocuments = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Get MongoDB URI - prefer prop, then localStorage, then undefined
      const uriToUse = mongodbUri?.trim() || localStorage.getItem('mongodb_uri')?.trim() || undefined;
      console.log('[RawDocumentList] Loading documents with MongoDB URI:', uriToUse ? 'Provided' : 'Not provided');
      
      const params: any = { limit: 100 };
      if (statusFilter) {
        params.status = statusFilter;
      }
      const result = await apiService.getRawDocuments(params, uriToUse);
      setDocuments(result.raw_documents || []);
    } catch (err: any) {
      const errorData = err.response?.data || {};
      const errorMessage = errorData.error || errorData.details || err.message || 'Failed to load documents';
      const errorType = errorData.type || '';
      const traceback = errorData.traceback || '';
      
      // Build detailed error message
      let fullErrorMessage = `Failed to load documents: ${errorMessage}`;
      if (errorType) {
        fullErrorMessage += ` (${errorType})`;
      }
      
      setError(fullErrorMessage);
      console.error('Error loading documents:', {
        error: errorMessage,
        type: errorType,
        response: errorData,
        traceback: traceback
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (id: string) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
    onSelectionChange(Array.from(newSelected));
  };

  const handleSelectAll = () => {
    const pendingDocs = documents.filter(d => d.status === 'pending');
    const newSelected = new Set(selectedIds);
    
    if (pendingDocs.every(d => newSelected.has(d.raw_document_id))) {
      // Deselect all pending
      pendingDocs.forEach(d => newSelected.delete(d.raw_document_id));
    } else {
      // Select all pending
      pendingDocs.forEach(d => newSelected.add(d.raw_document_id));
    }
    
    setSelectedIds(newSelected);
    onSelectionChange(Array.from(newSelected));
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this raw document?')) return;
    
    try {
      await apiService.deleteRawDocument(id);
      loadDocuments();
      const newSelected = new Set(selectedIds);
      newSelected.delete(id);
      setSelectedIds(newSelected);
      onSelectionChange(Array.from(newSelected));
    } catch (err: any) {
      alert(`Failed to delete document: ${err.message}`);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'processed':
        return 'bg-green-100 text-green-800';
      case 'processing':
        return 'bg-blue-100 text-blue-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="raw-document-list">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Raw Documents</h3>
        <div className="flex gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="p-2 border rounded"
          >
            <option value="">All Status</option>
            <option value="pending">Pending</option>
            <option value="processing">Processing</option>
            <option value="processed">Processed</option>
            <option value="failed">Failed</option>
          </select>
          <button
            onClick={loadDocuments}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          >
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-8">Loading documents...</div>
      ) : documents.length === 0 ? (
        <div className="text-center py-8 text-gray-500">No raw documents found</div>
      ) : (
        <>
          <div className="mb-2">
            <button
              onClick={handleSelectAll}
              className="text-sm text-blue-600 hover:underline"
            >
              {documents.filter(d => d.status === 'pending').every(d => selectedIds.has(d.raw_document_id))
                ? 'Deselect All Pending'
                : 'Select All Pending'}
            </button>
          </div>
          
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {documents.map((doc) => (
              <div
                key={doc.raw_document_id}
                className={`p-3 border rounded ${
                  selectedIds.has(doc.raw_document_id) ? 'bg-blue-50 border-blue-300' : 'bg-white'
                }`}
              >
                <div className="flex items-start gap-3">
                  {doc.status === 'pending' && (
                    <input
                      type="checkbox"
                      checked={selectedIds.has(doc.raw_document_id)}
                      onChange={() => handleSelect(doc.raw_document_id)}
                      className="mt-1"
                    />
                  )}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium">
                        {doc.metadata?.file_name || doc.origin_id}
                      </span>
                      <span className={`px-2 py-1 text-xs rounded ${getStatusColor(doc.status)}`}>
                        {doc.status}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600">
                      <div>Source: {doc.origin_source_type}</div>
                      <div>Origin ID: {doc.origin_id}</div>
                      <div>Created: {new Date(doc.created_at).toLocaleString()}</div>
                      {doc.error_message && (
                        <div className="text-red-600 mt-1">Error: {doc.error_message}</div>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(doc.raw_document_id)}
                    className="px-2 py-1 text-sm text-red-600 hover:bg-red-50 rounded"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
          
          <div className="mt-4 text-sm text-gray-600">
            {selectedIds.size} document(s) selected
          </div>
        </>
      )}
    </div>
  );
};

