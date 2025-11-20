import React, { useState, useEffect } from 'react';
import { apiService } from '../api';

interface DatabaseCollectionSelectorProps {
  label: string;
  value: string; // Format: "database.collection" or "collection"
  onChange: (value: string) => void;
  mongodbUri: string;
  connectionId?: string | null;
  placeholder?: string;
  required?: boolean;
}

export const DatabaseCollectionSelector: React.FC<DatabaseCollectionSelectorProps> = ({
  label,
  value,
  onChange,
  mongodbUri,
  connectionId,
  required = false
}) => {
  const [databases, setDatabases] = useState<any[]>([]);
  const [selectedDatabase, setSelectedDatabase] = useState<string>('');
  const [selectedCollection, setSelectedCollection] = useState<string>('');
  const [collections, setCollections] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Parse initial value
  useEffect(() => {
    if (value && value.includes('.')) {
      const [db, coll] = value.split('.', 2);
      setSelectedDatabase(db);
      setSelectedCollection(coll);
    } else if (value) {
      setSelectedCollection(value);
    }
  }, [value]);

  // Load databases
  useEffect(() => {
    loadDatabases();
  }, [mongodbUri, connectionId]);

  // Load collections when database changes
  useEffect(() => {
    if (selectedDatabase) {
      loadCollections(selectedDatabase);
    } else {
      setCollections([]);
      setSelectedCollection('');
    }
  }, [selectedDatabase, mongodbUri, connectionId]);

  // Update parent when selection changes
  useEffect(() => {
    if (selectedDatabase && selectedCollection) {
      onChange(`${selectedDatabase}.${selectedCollection}`);
    } else if (selectedCollection && !selectedDatabase) {
      onChange(selectedCollection);
    } else {
      onChange('');
    }
  }, [selectedDatabase, selectedCollection, onChange]);

  const loadDatabases = async () => {
    if (!mongodbUri && !connectionId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const databasesList = await apiService.getDatabases(connectionId || undefined, mongodbUri);
      setDatabases(databasesList || []);
    } catch (err: any) {
      setError(`Failed to load databases: ${err.message}`);
      console.error('Error loading databases:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadCollections = async (databaseName: string) => {
    if (!mongodbUri && !connectionId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const databasesList = await apiService.getDatabases(connectionId || undefined, mongodbUri);
      const db = databasesList.find((d: any) => d.name === databaseName);
      setCollections(db?.collections || []);
    } catch (err: any) {
      setError(`Failed to load collections: ${err.message}`);
      console.error('Error loading collections:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="database-collection-selector">
      <label className="block text-sm font-medium mb-2">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      
      {error && (
        <div className="mb-2 p-2 bg-red-100 border border-red-400 text-red-700 text-sm rounded">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        {/* Database Selector */}
        <div>
          <label className="block text-xs text-gray-600 mb-1">Database</label>
          <select
            value={selectedDatabase}
            onChange={(e) => {
              setSelectedDatabase(e.target.value);
              setSelectedCollection(''); // Reset collection when database changes
            }}
            disabled={loading}
            className="w-full p-2 border rounded text-sm"
          >
            <option value="">Select database...</option>
            {databases.map((db) => (
              <option key={db.name} value={db.name}>
                {db.name}
              </option>
            ))}
          </select>
        </div>

        {/* Collection Selector */}
        <div>
          <label className="block text-xs text-gray-600 mb-1">Collection</label>
          <select
            value={selectedCollection}
            onChange={(e) => setSelectedCollection(e.target.value)}
            disabled={loading || !selectedDatabase}
            className="w-full p-2 border rounded text-sm"
          >
            <option value="">Select collection...</option>
            {collections.map((coll) => (
              <option key={coll} value={coll}>
                {coll}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Display selected value */}
      {value && (
        <div className="mt-2 text-xs text-gray-600">
          Selected: <span className="font-mono font-semibold">{value}</span>
        </div>
      )}

      {loading && (
        <div className="mt-2 text-xs text-gray-500">Loading...</div>
      )}
    </div>
  );
};

