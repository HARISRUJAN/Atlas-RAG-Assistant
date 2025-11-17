/**
 * Connection selector component for choosing active connection
 */

import { useState, useEffect } from 'react';
import { apiService } from '../api';
import type { Connection } from '../types';
import ProviderBadge from './ProviderBadge';

interface ConnectionSelectorProps {
  selectedConnectionId: string | null;
  onConnectionChange: (connectionId: string | null) => void;
  onAddConnection: () => void;
}

const ConnectionSelector: React.FC<ConnectionSelectorProps> = ({
  selectedConnectionId,
  onConnectionChange,
  onAddConnection,
}) => {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    loadConnections();
  }, []);

  const loadConnections = async () => {
    setIsLoading(true);
    setError('');
    try {
      const conns = await apiService.getConnections();
      setConnections(conns);
      
      // Auto-select first connection if none selected
      if (!selectedConnectionId && conns.length > 0) {
        onConnectionChange(conns[0].connection_id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load connections');
    } finally {
      setIsLoading(false);
    }
  };

  const getConnectionStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'var(--color-accent-green)';
      case 'error':
        return '#ef4444';
      default:
        return '#FFA500';
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="block text-sm font-medium text-gray-700">Connection</label>
        <button
          onClick={onAddConnection}
          className="text-xs px-2 py-1 rounded font-medium hover:bg-gray-100"
          style={{ color: 'var(--color-accent-green)' }}
        >
          + Add
        </button>
      </div>

      {isLoading ? (
        <div className="text-xs text-gray-500">Loading connections...</div>
      ) : error ? (
        <div className="text-xs text-red-600">{error}</div>
      ) : connections.length === 0 ? (
        <div className="text-xs text-gray-500">
          No connections. <button onClick={onAddConnection} className="underline">Add one</button>
        </div>
      ) : (
        <div className="space-y-1">
          <select
            value={selectedConnectionId || ''}
            onChange={(e) => onConnectionChange(e.target.value || null)}
            className="w-full text-xs px-2 py-1.5 border rounded focus:outline-none focus:ring-1 focus:ring-green-500"
            style={{ borderColor: 'var(--color-border-muted)' }}
          >
            <option value="">Select connection...</option>
            {connections.map((conn) => (
              <option key={conn.connection_id} value={conn.connection_id}>
                {conn.display_name}
              </option>
            ))}
          </select>

          {selectedConnectionId && (
            <div className="flex items-center space-x-2 text-xs">
              <div
                className="h-2 w-2 rounded-full"
                style={{
                  backgroundColor: getConnectionStatusColor(
                    connections.find(c => c.connection_id === selectedConnectionId)?.status || 'inactive'
                  ),
                }}
              />
              <span style={{ color: 'var(--color-text-muted)' }}>
                {connections.find(c => c.connection_id === selectedConnectionId)?.status || 'unknown'}
              </span>
              {selectedConnectionId && (
                <ProviderBadge
                  provider={connections.find(c => c.connection_id === selectedConnectionId)?.provider || 'mongo'}
                  size="sm"
                />
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ConnectionSelector;

