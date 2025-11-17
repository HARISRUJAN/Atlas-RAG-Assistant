/**
 * Connection list component for managing connections
 */

import { useState } from 'react';
import { apiService } from '../api';
import type { Connection } from '../types';
import ProviderBadge from './ProviderBadge';

interface ConnectionListProps {
  connections: Connection[];
  onRefresh: () => void;
  onEdit?: (connection: Connection) => void;
}

const ConnectionList: React.FC<ConnectionListProps> = ({ connections, onRefresh, onEdit }) => {
  const [testingIds, setTestingIds] = useState<Set<string>>(new Set());
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set());

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'var(--color-accent-green)';
      case 'error':
        return '#ef4444';
      default:
        return '#FFA500';
    }
  };

  const handleTest = async (connectionId: string) => {
    setTestingIds(prev => new Set(prev).add(connectionId));
    try {
      await apiService.testConnection(connectionId);
      onRefresh();
    } catch (err) {
      console.error('Test failed:', err);
    } finally {
      setTestingIds(prev => {
        const next = new Set(prev);
        next.delete(connectionId);
        return next;
      });
    }
  };

  const handleDelete = async (connectionId: string) => {
    if (!confirm('Are you sure you want to delete this connection?')) {
      return;
    }
    setDeletingIds(prev => new Set(prev).add(connectionId));
    try {
      await apiService.deleteConnection(connectionId);
      onRefresh();
    } catch (err) {
      console.error('Delete failed:', err);
    } finally {
      setDeletingIds(prev => {
        const next = new Set(prev);
        next.delete(connectionId);
        return next;
      });
    }
  };

  if (connections.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-gray-500">No connections yet. Create one to get started.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {connections.map((conn) => (
        <div
          key={conn.connection_id}
          className="p-3 border rounded-lg hover:bg-gray-50"
          style={{ borderColor: 'var(--color-border-muted)' }}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 flex-1 min-w-0">
              <div
                className="h-2 w-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: getStatusColor(conn.status) }}
              />
              <ProviderBadge provider={conn.provider} size="sm" />
              <span className="font-medium text-sm truncate" style={{ color: 'var(--color-text-dark)' }}>
                {conn.display_name}
              </span>
            </div>
            <div className="flex items-center space-x-2 flex-shrink-0">
              <button
                onClick={() => handleTest(conn.connection_id)}
                disabled={testingIds.has(conn.connection_id)}
                className="text-xs px-2 py-1 rounded hover:bg-gray-100 disabled:opacity-50"
                style={{ color: 'var(--color-accent-green)' }}
                title="Test connection"
              >
                {testingIds.has(conn.connection_id) ? 'Testing...' : 'Test'}
              </button>
              {onEdit && (
                <button
                  onClick={() => onEdit(conn)}
                  className="text-xs px-2 py-1 rounded hover:bg-gray-100"
                  style={{ color: 'var(--color-text-muted)' }}
                  title="Edit connection"
                >
                  Edit
                </button>
              )}
              <button
                onClick={() => handleDelete(conn.connection_id)}
                disabled={deletingIds.has(conn.connection_id)}
                className="text-xs px-2 py-1 rounded hover:bg-red-50 disabled:opacity-50"
                style={{ color: '#ef4444' }}
                title="Delete connection"
              >
                {deletingIds.has(conn.connection_id) ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
          <div className="mt-2 flex items-center space-x-2 text-xs" style={{ color: 'var(--color-text-muted)' }}>
            <span>Status: {conn.status}</span>
            <span>•</span>
            <span>{conn.scopes.length} scope{conn.scopes.length !== 1 ? 's' : ''}</span>
          </div>
        </div>
      ))}
    </div>
  );
};

export default ConnectionList;

