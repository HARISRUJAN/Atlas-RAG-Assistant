/**
 * Collection selector component for choosing MongoDB collections
 */

import { useState, useEffect, useRef } from 'react';
import { apiService } from '../api';
import type { Database } from '../types';
import ConnectionSelector from './ConnectionSelector';
import ConnectionModal from './ConnectionModal';
import ProviderBadge from './ProviderBadge';

// Component for database checkbox with indeterminate state
const DatabaseCheckbox: React.FC<{
  dbName: string;
  selectionState: 'all' | 'some' | 'none';
  onToggle: (dbName: string, e?: React.MouseEvent | React.ChangeEvent) => void;
}> = ({ dbName, selectionState, onToggle }) => {
  const checkboxRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (checkboxRef.current) {
      checkboxRef.current.indeterminate = selectionState === 'some';
    }
  }, [selectionState]);

  return (
    <input
      ref={checkboxRef}
      type="checkbox"
      checked={selectionState === 'all'}
      onChange={(e) => onToggle(dbName, e)}
      onClick={(e) => e.stopPropagation()}
      className="h-4 w-4 rounded cursor-pointer"
      style={{ 
        accentColor: 'var(--color-accent-green)',
        borderColor: 'var(--color-border-muted)'
      }}
    />
  );
};

interface CollectionSelectorProps {
  selectedCollections: Set<string>;
  onCollectionsChange: (collections: Set<string>) => void;
  mongodbUri: string; // For backward compatibility
  onMongodbUriChange: (uri: string) => void; // For backward compatibility
  connectionId?: string | null; // New: connection ID
  onConnectionIdChange?: (connectionId: string | null) => void; // New: connection ID change handler
}

const CollectionSelector: React.FC<CollectionSelectorProps> = ({ 
  selectedCollections, 
  onCollectionsChange,
  mongodbUri,
  onMongodbUriChange,
  connectionId: propConnectionId,
  onConnectionIdChange: propOnConnectionIdChange
}) => {
  const [databases, setDatabases] = useState<Database[]>([]);
  const [expandedDatabases, setExpandedDatabases] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [uriInput, setUriInput] = useState<string>('');
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'testing'>('disconnected');
  const [connectionId, setConnectionId] = useState<string | null>(propConnectionId || null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [connectionProvider, setConnectionProvider] = useState<string | null>(null);

  useEffect(() => {
    // Load default URI from backend on mount
    loadDefaultUri();
  }, []);

  useEffect(() => {
    // Update URI input when prop changes
    if (mongodbUri) {
      setUriInput(mongodbUri);
    }
  }, [mongodbUri]);

  useEffect(() => {
    // Use connection_id if available, otherwise fall back to MongoDB URI
    if (connectionId) {
      fetchConnectionCollections();
    } else if (mongodbUri && mongodbUri.trim()) {
      fetchDatabases();
    } else {
      setIsLoading(false);
    }
  }, [connectionId, mongodbUri]);

  // Listen for collections refresh events (e.g., after ingestion)
  useEffect(() => {
    const handleRefresh = () => {
      if (connectionId) {
        fetchConnectionCollections();
      } else if (mongodbUri && mongodbUri.trim()) {
        fetchDatabases();
      }
    };

    window.addEventListener('collections-refresh', handleRefresh);
    return () => {
      window.removeEventListener('collections-refresh', handleRefresh);
    };
  }, [connectionId, mongodbUri]);

  const handleConnectionIdChange = (newConnectionId: string | null) => {
    setConnectionId(newConnectionId);
    if (propOnConnectionIdChange) {
      propOnConnectionIdChange(newConnectionId);
    }
  };

  const fetchConnectionCollections = async () => {
    if (!connectionId) return;
    
    setIsLoading(true);
    setError('');
    try {
      console.log(`Fetching collections for connection: ${connectionId}`);
      const response = await apiService.getConnectionCollections(connectionId);
      setConnectionProvider(response.provider);
      
      // Format collections based on provider
      if (response.provider === 'mongo') {
        // For MongoDB, use existing getDatabases
        const dbs = await apiService.getDatabases(connectionId);
        console.log(`Loaded ${dbs.length} MongoDB databases via connection ID`);
        setDatabases(dbs);
      } else {
        // For other providers, create a flat list structure
        const flatDatabases: Database[] = [{
          name: response.provider,
          collections: response.collections
        }];
        console.log(`Loaded ${response.collections.length} collections from ${response.provider}`);
        setDatabases(flatDatabases);
      }
      
      setConnectionStatus('connected');
    } catch (err: any) {
      setConnectionStatus('disconnected');
      setError(err.response?.data?.error || err.message || 'Failed to load collections');
    } finally {
      setIsLoading(false);
    }
  };

  const loadDefaultUri = async () => {
    try {
      // Use relative URL to leverage Vite proxy
      const apiBase = import.meta.env.VITE_API_URL || '/api';
      const response = await fetch(`${apiBase}/config/mongodb-uri`);
      if (response.ok) {
        const data = await response.json();
        if (data.default_uri) {
          // Check localStorage first, then use default
          const storedUri = localStorage.getItem('mongodb_uri');
          if (storedUri) {
            setUriInput(storedUri);
            onMongodbUriChange(storedUri);
          } else {
            setUriInput(data.default_uri);
            onMongodbUriChange(data.default_uri);
            localStorage.setItem('mongodb_uri', data.default_uri);
          }
        }
      } else {
        // If config endpoint fails, try localStorage
        const storedUri = localStorage.getItem('mongodb_uri');
        if (storedUri) {
          setUriInput(storedUri);
          onMongodbUriChange(storedUri);
        }
      }
    } catch (err) {
      console.error('Error loading default URI:', err);
      // Use stored URI from localStorage if available
      const storedUri = localStorage.getItem('mongodb_uri');
      if (storedUri) {
        setUriInput(storedUri);
        onMongodbUriChange(storedUri);
      }
    }
  };

  const handleConnect = async () => {
    if (!uriInput.trim()) {
      setError('Please enter a MongoDB URI');
      return;
    }

    setIsConnecting(true);
    setConnectionStatus('testing');
    setError('');
    
    try {
      // Test connection by trying to fetch databases
      await apiService.getDatabases(undefined, uriInput.trim());
      setConnectionStatus('connected');
      
      // Save to localStorage
      localStorage.setItem('mongodb_uri', uriInput.trim());
      onMongodbUriChange(uriInput.trim());
      
      // Refresh databases will happen automatically via useEffect
    } catch (err: any) {
      setConnectionStatus('disconnected');
      
      // Better error handling for network errors
      let errorMessage = 'Connection failed';
      
      if (err.code === 'ERR_NETWORK' || err.message === 'Network Error' || !err.response) {
        const backendUrl = import.meta.env.VITE_API_URL || '/api';
        const baseUrl = backendUrl.replace('/api', '');
        errorMessage = `Cannot connect to backend server. Please ensure the backend is running on ${baseUrl}`;
      } else if (err.response?.data?.error) {
        errorMessage = err.response.data.error;
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
      console.error('Connection error:', err);
    } finally {
      setIsConnecting(false);
    }
  };

  const fetchDatabases = async () => {
    if (!mongodbUri || !mongodbUri.trim()) {
      setIsLoading(false);
      return;
    }
    
    setIsLoading(true);
    setError('');
    try {
      console.log('Fetching databases with MongoDB URI...');
      const databasesList = await apiService.getDatabases(undefined, mongodbUri);
      console.log(`Loaded ${databasesList.length} databases`);
      setDatabases(databasesList);
      setConnectionStatus('connected');
      
      // Auto-expand first database
      if (databasesList.length > 0) {
        setExpandedDatabases(new Set([databasesList[0].name]));
      }
      
      // Auto-select first queryable collection if none selected (exclude raw_documents)
      if (selectedCollections.size === 0 && databasesList.length > 0) {
        const firstQueryableCollection = databasesList
          .flatMap(db => db.collections
            .filter(coll => !coll.includes('raw_documents'))
            .map(coll => `${db.name}.${coll}`)
          )[0];
        if (firstQueryableCollection) {
          onCollectionsChange(new Set([firstQueryableCollection]));
        }
      }
    } catch (err: any) {
      setConnectionStatus('disconnected');
      
      // Better error handling for network errors
      let errorMessage = 'Failed to load databases';
      
      if (err.code === 'ERR_NETWORK' || err.message === 'Network Error' || !err.response) {
        const backendUrl = import.meta.env.VITE_API_URL || '/api';
        const baseUrl = backendUrl.replace('/api', '');
        errorMessage = `Cannot connect to backend server. Please ensure the backend is running on ${baseUrl}`;
      } else if (err.response?.data?.error) {
        errorMessage = err.response.data.error;
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
      console.error('Error fetching databases:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleDatabase = (dbName: string) => {
    setExpandedDatabases(prev => {
      const newSet = new Set(prev);
      if (newSet.has(dbName)) {
        newSet.delete(dbName);
      } else {
        newSet.add(dbName);
      }
      return newSet;
    });
  };

  const handleCollectionToggle = (dbName: string, collectionName: string, e?: React.MouseEvent | React.ChangeEvent) => {
    if (e) {
      e.stopPropagation();
    }
    const fullPath = `${dbName}.${collectionName}`;
    const newSelections = new Set(selectedCollections);
    if (newSelections.has(fullPath)) {
      newSelections.delete(fullPath);
    } else {
      newSelections.add(fullPath);
    }
    onCollectionsChange(newSelections);
  };

  const handleDatabaseToggle = (dbName: string, e?: React.MouseEvent | React.ChangeEvent) => {
    if (e) {
      e.stopPropagation();
    }
    const database = databases.find(db => db.name === dbName);
    if (!database) return;

    // Filter out raw_documents when toggling database
    const dbCollections = database.collections
      .filter(coll => !coll.includes('raw_documents'))
      .map(coll => `${dbName}.${coll}`);
    const allSelected = dbCollections.every(path => selectedCollections.has(path));
    
    const newSelections = new Set(selectedCollections);
    if (allSelected) {
      // Deselect all collections in this database
      dbCollections.forEach(path => newSelections.delete(path));
    } else {
      // Select all collections in this database
      dbCollections.forEach(path => newSelections.add(path));
    }
    onCollectionsChange(newSelections);
  };

  const getDatabaseSelectionState = (dbName: string): 'all' | 'some' | 'none' => {
    const database = databases.find(db => db.name === dbName);
    if (!database) return 'none';

    // Filter out raw_documents when checking selection state
    const dbCollections = database.collections
      .filter(coll => !coll.includes('raw_documents'))
      .map(coll => `${dbName}.${coll}`);
    const selectedCount = dbCollections.filter(path => selectedCollections.has(path)).length;
    
    if (selectedCount === 0) return 'none';
    if (selectedCount === dbCollections.length) return 'all';
    return 'some';
  };


  return (
    <div className="h-full flex flex-col">
      {/* Connection Section */}
      <div className="p-4 border-b" style={{ borderColor: 'var(--color-border-muted)', backgroundColor: '#f9fafb' }}>
        <h3 className="text-sm font-semibold text-mongodb-darkGray mb-2">
          Vector Store Connection
        </h3>
        {connectionId ? (
          <ConnectionSelector
            selectedConnectionId={connectionId}
            onConnectionChange={handleConnectionIdChange}
            onAddConnection={() => setIsModalOpen(true)}
          />
        ) : (
          // Fallback to MongoDB URI input for backward compatibility
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <input
                type="text"
                value={uriInput}
                onChange={(e) => setUriInput(e.target.value)}
                placeholder="mongodb+srv://..."
                className="flex-1 text-xs px-2 py-1.5 border rounded focus:outline-none focus:ring-1 focus:ring-green-500"
                style={{ borderColor: 'var(--color-border-muted)' }}
                disabled={isConnecting}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !isConnecting && uriInput.trim()) {
                    handleConnect();
                  }
                }}
              />
              <button
                onClick={handleConnect}
                disabled={isConnecting || !uriInput.trim()}
                className="px-3 py-1.5 text-xs rounded font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                style={{
                  backgroundColor: 'var(--color-accent-green)',
                  color: 'white'
                }}
              >
                {isConnecting ? (
                  <div className="spinner" style={{ width: '12px', height: '12px' }}></div>
                ) : (
                  'Connect'
                )}
              </button>
            </div>
            <div className="flex items-center space-x-2">
              <div 
                className="h-2 w-2 rounded-full"
                style={{ 
                  backgroundColor: connectionStatus === 'connected' 
                    ? 'var(--color-accent-green)' 
                    : connectionStatus === 'testing'
                    ? '#FFA500'
                    : '#ef4444'
                }}
              ></div>
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                {connectionStatus === 'connected' ? 'Connected' : connectionStatus === 'testing' ? 'Testing...' : 'Disconnected'}
              </span>
            </div>
            <div className="text-xs text-gray-500">
              <button onClick={() => setIsModalOpen(true)} className="underline">
                Or use multi-provider connections
              </button>
            </div>
            {error && (
              <div className="text-xs text-red-600 mt-1 break-words">{error}</div>
            )}
          </div>
        )}
      </div>

      {/* Connection Modal */}
      <ConnectionModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onConnectionSelected={(id) => {
          handleConnectionIdChange(id);
          setIsModalOpen(false);
        }}
      />

      {/* Header */}
      <div className="p-4 border-b flex items-center justify-between" style={{ borderColor: 'var(--color-border-muted)' }}>
        <h2 className="text-lg font-semibold text-mongodb-darkGray">
          Collections
        </h2>
        <button
          onClick={() => connectionId ? fetchConnectionCollections() : fetchDatabases()}
          className="text-sm p-1 rounded hover:bg-gray-100"
          style={{ color: 'var(--color-accent-green)' }}
          title="Refresh collections"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>
      
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-8">
            <div className="spinner mb-4" style={{ width: '24px', height: '24px' }}></div>
            <span className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Loading collections...</span>
          </div>
        ) : error ? (
          <div className="p-4 bg-red-50 border-l-4 border-red-500 rounded-r-md">
            <p className="text-red-700 font-medium text-sm">Error: {error}</p>
            <button
              onClick={() => connectionId ? fetchConnectionCollections() : fetchDatabases()}
              className="mt-2 text-sm text-red-700 underline hover:text-red-900"
            >
              Retry
            </button>
          </div>
        ) : databases.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
              No databases found. Please connect to MongoDB.
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            {databases.map((database) => {
              const isExpanded = expandedDatabases.has(database.name);
              // Use metadata if available, otherwise fall back to simple collections list
              const collectionsWithMetadata = database.collections_metadata || 
                database.collections.map(name => ({ name, type: 'origin' as const, is_semantic: false }));
              
              // Filter out raw_documents collections - they are not queryable vector collections
              const queryableCollections = collectionsWithMetadata.filter(
                coll => !coll.name.includes('raw_documents')
              );
              const totalCollections = queryableCollections.length;
              
              return (
                <div key={database.name} className="border rounded-lg" style={{ borderColor: 'var(--color-border-muted)' }}>
                  {/* Database Header */}
                  <div
                    onClick={() => toggleDatabase(database.name)}
                    className="p-2 cursor-pointer hover:bg-gray-50 transition-colors flex items-center justify-between"
                  >
                    <div className="flex items-center space-x-2 flex-1 min-w-0">
                      <svg
                        className={`h-4 w-4 transition-transform flex-shrink-0 ${isExpanded ? 'rotate-90' : ''}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        style={{ color: 'var(--color-text-muted)' }}
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                      {/* Database Checkbox */}
                      <DatabaseCheckbox
                        key={`${database.name}-${getDatabaseSelectionState(database.name)}`}
                        dbName={database.name}
                        selectionState={getDatabaseSelectionState(database.name)}
                        onToggle={handleDatabaseToggle}
                      />
                      <svg
                        className="h-4 w-4 flex-shrink-0"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        style={{ color: 'var(--color-accent-green)' }}
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                      </svg>
                      <span className="font-medium text-sm truncate" style={{ color: 'var(--color-text-dark)' }}>
                        {database.name}
                      </span>
                      {connectionProvider && connectionProvider !== 'mongo' && (
                        <ProviderBadge provider={connectionProvider as any} size="sm" />
                      )}
                    </div>
                    <span className="text-xs px-2 py-0.5 rounded ml-2" style={{ 
                      backgroundColor: 'var(--color-accent-green)', 
                      color: 'white'
                    }}>
                      {totalCollections}
                    </span>
                  </div>
                  
                  {/* Collections List */}
                  {isExpanded && (
                    <div className="border-t pl-4 pr-2 py-1" style={{ borderColor: 'var(--color-border-muted)' }}>
                      {queryableCollections.map((collectionInfo) => {
                        const collection = typeof collectionInfo === 'string' ? collectionInfo : collectionInfo.name;
                        const isSemantic = typeof collectionInfo === 'object' ? collectionInfo.is_semantic : collection.endsWith('_semantic');
                        const fullPath = `${database.name}.${collection}`;
                        const isSelected = selectedCollections.has(fullPath);
                        
                        return (
                          <div
                            key={collection}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleCollectionToggle(database.name, collection);
                            }}
                            className={`p-2 mb-1 rounded cursor-pointer transition-all ${
                              isSelected
                                ? 'bg-green-50 border'
                                : 'hover:bg-gray-50'
                            }`}
                            style={{
                              borderColor: isSelected ? 'var(--color-accent-green)' : 'transparent'
                            }}
                          >
                            <div className="flex items-center space-x-2">
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => {
                                  handleCollectionToggle(database.name, collection);
                                }}
                                onClick={(e) => e.stopPropagation()}
                                className="h-4 w-4 rounded cursor-pointer"
                                style={{ 
                                  accentColor: 'var(--color-accent-green)',
                                  borderColor: 'var(--color-border-muted)'
                                }}
                              />
                              <svg
                                className="h-3 w-3 flex-shrink-0"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                                style={{ color: isSelected ? 'var(--color-accent-green)' : 'var(--color-text-muted)' }}
                              >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                              </svg>
                              <div className="flex items-center gap-1.5 flex-1 min-w-0">
                                {isSemantic && (
                                  <span 
                                    className="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-medium flex-shrink-0" 
                                    title="Semantic collection (for RAG queries)"
                                  >
                                    🔍
                                  </span>
                                )}
                                <span className={`text-xs truncate ${isSelected ? 'font-medium' : ''}`} style={{ 
                                  color: isSelected ? 'var(--color-text-dark)' : 'var(--color-text-muted)'
                                }}>
                                  {collection}
                                </span>
                              </div>
                              {connectionProvider && (
                                <ProviderBadge provider={connectionProvider as any} size="sm" />
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
      
      {/* Footer */}
      {databases.length > 0 && (
        <div className="p-4 border-t text-xs" style={{ borderColor: 'var(--color-border-muted)', color: 'var(--color-text-muted)' }}>
          <div className="flex items-center justify-between">
            <span>
              {databases.length} database{databases.length !== 1 ? 's' : ''} • {' '}
              {databases.reduce((sum, db) => sum + db.collections.length, 0)} collection{databases.reduce((sum, db) => sum + db.collections.length, 0) !== 1 ? 's' : ''}
            </span>
            {selectedCollections.size > 0 && (
              <span className="font-medium" style={{ color: 'var(--color-accent-green)' }}>
                {selectedCollections.size} selected
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default CollectionSelector;
