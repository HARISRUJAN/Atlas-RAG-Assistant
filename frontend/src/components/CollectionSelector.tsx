/**
 * Collection selector component for choosing MongoDB collections
 */

import { useState, useEffect } from 'react';
import { apiService } from '../api';
import type { Database } from '../types';

interface CollectionSelectorProps {
  selectedCollection: string | null;
  onCollectionChange: (collectionName: string | null) => void;
}

const CollectionSelector: React.FC<CollectionSelectorProps> = ({ 
  selectedCollection, 
  onCollectionChange 
}) => {
  const [databases, setDatabases] = useState<Database[]>([]);
  const [expandedDatabases, setExpandedDatabases] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    fetchDatabases();
  }, []);

  const fetchDatabases = async () => {
    setIsLoading(true);
    setError('');
    try {
      const databasesList = await apiService.getDatabases();
      setDatabases(databasesList);
      
      // Auto-expand first database
      if (databasesList.length > 0) {
        setExpandedDatabases(new Set([databasesList[0].name]));
      }
      
      // Auto-select first collection if none selected
      if (!selectedCollection && databasesList.length > 0 && databasesList[0].collections.length > 0) {
        const firstCollection = `${databasesList[0].name}.${databasesList[0].collections[0]}`;
        onCollectionChange(firstCollection);
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.message || 'Failed to load databases';
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

  const handleCollectionClick = (dbName: string, collectionName: string) => {
    const fullPath = `${dbName}.${collectionName}`;
    onCollectionChange(fullPath);
  };


  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b flex items-center justify-between" style={{ borderColor: 'var(--color-border-muted)' }}>
        <h2 className="text-lg font-semibold text-mongodb-darkGray">
          Collections
        </h2>
        <button
          onClick={fetchDatabases}
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
              onClick={fetchDatabases}
              className="mt-2 text-sm text-red-700 underline hover:text-red-900"
            >
              Retry
            </button>
          </div>
        ) : databases.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
              No databases found
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            {databases.map((database) => {
              const isExpanded = expandedDatabases.has(database.name);
              const totalCollections = database.collections.length;
              
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
                      {database.collections.map((collection) => {
                        const fullPath = `${database.name}.${collection}`;
                        const isSelected = selectedCollection === fullPath;
                        
                        return (
                          <div
                            key={collection}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleCollectionClick(database.name, collection);
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
                              {isSelected && (
                                <svg className="h-4 w-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20" style={{ color: 'var(--color-accent-green)' }}>
                                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                </svg>
                              )}
                              <svg
                                className="h-3 w-3 flex-shrink-0"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                                style={{ color: 'var(--color-text-muted)' }}
                              >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                              </svg>
                              <span className={`text-xs truncate ${isSelected ? 'font-medium' : ''}`} style={{ 
                                color: isSelected ? 'var(--color-text-dark)' : 'var(--color-text-muted)'
                              }}>
                                {collection}
                              </span>
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
          {databases.length} database{databases.length !== 1 ? 's' : ''} • {' '}
          {databases.reduce((sum, db) => sum + db.collections.length, 0)} collection{databases.reduce((sum, db) => sum + db.collections.length, 0) !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
};

export default CollectionSelector;

