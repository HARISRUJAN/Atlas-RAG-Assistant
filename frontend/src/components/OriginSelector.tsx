import React, { useState, useEffect } from 'react';
import { apiService } from '../api';

interface OriginSourceType {
  type: string;
  name: string;
  description: string;
  required_config: string[];
}

interface OriginSelectorProps {
  onSelect?: (sourceType: string, connectionConfig: any) => void;
  onDocumentsLoaded: (documents: any[]) => void;
}

export const OriginSelector: React.FC<OriginSelectorProps> = ({ onSelect: _onSelect, onDocumentsLoaded }) => {
  const [sourceTypes, setSourceTypes] = useState<OriginSourceType[]>([]);
  const [selectedType, setSelectedType] = useState<string>('');
  const [connectionConfig, setConnectionConfig] = useState<any>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    loadSourceTypes();
  }, []);

  const loadSourceTypes = async () => {
    try {
      const types = await apiService.getOriginSourceTypes();
      setSourceTypes(types);
    } catch (err: any) {
      setError(`Failed to load source types: ${err.message}`);
    }
  };

  const handleTestConnection = async () => {
    if (!selectedType) return;
    
    setTesting(true);
    setError(null);
    
    try {
      const result = await apiService.testOriginConnection(selectedType, connectionConfig);
      if (result.status === 'connected') {
        alert('Connection successful!');
      } else {
        setError(result.message);
      }
    } catch (err: any) {
      setError(`Connection test failed: ${err.message}`);
    } finally {
      setTesting(false);
    }
  };

  const handleLoadDocuments = async () => {
    if (!selectedType) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const result = await apiService.listOriginDocuments(selectedType, connectionConfig, 100, 0);
      setDocuments(result.documents || []);
      onDocumentsLoaded(result.documents || []);
    } catch (err: any) {
      setError(`Failed to load documents: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleConfigChange = (key: string, value: string) => {
    setConnectionConfig((prev: any) => ({
      ...prev,
      [key]: value
    }));
  };

  const selectedSourceType = sourceTypes.find(st => st.type === selectedType);

  return (
    <div className="origin-selector p-4 border rounded-lg bg-white">
      <h3 className="text-lg font-semibold mb-4">Select Origin Source</h3>
      
      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Source Type</label>
        <select
          value={selectedType}
          onChange={(e) => setSelectedType(e.target.value)}
          className="w-full p-2 border rounded"
        >
          <option value="">Select a source type...</option>
          {sourceTypes.map((st) => (
            <option key={st.type} value={st.type}>
              {st.name}
            </option>
          ))}
        </select>
      </div>

      {selectedSourceType && (
        <div className="mb-4">
          <p className="text-sm text-gray-600 mb-3">{selectedSourceType.description}</p>
          
          <div className="space-y-3">
            {selectedSourceType.required_config.map((configKey) => (
              <div key={configKey}>
                <label className="block text-sm font-medium mb-1">
                  {configKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </label>
                <input
                  type={configKey.includes('key') || configKey.includes('password') ? 'password' : 'text'}
                  value={connectionConfig[configKey] || ''}
                  onChange={(e) => handleConfigChange(configKey, e.target.value)}
                  className="w-full p-2 border rounded"
                  placeholder={`Enter ${configKey}`}
                />
              </div>
            ))}
          </div>

          <div className="mt-4 flex gap-2">
            <button
              onClick={handleTestConnection}
              disabled={testing}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
            >
              {testing ? 'Testing...' : 'Test Connection'}
            </button>
            <button
              onClick={handleLoadDocuments}
              disabled={loading}
              className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
            >
              {loading ? 'Loading...' : 'Load Documents'}
            </button>
          </div>
        </div>
      )}

      {documents.length > 0 && (
        <div className="mt-4">
          <p className="text-sm text-gray-600 mb-2">
            Found {documents.length} document(s)
          </p>
        </div>
      )}
    </div>
  );
};

