/**
 * Connection management modal component
 */

import { useState, useEffect } from 'react';
import { apiService } from '../api';
import type { Connection } from '../types';
import ProviderConnectForm from './ProviderConnectForm';
import ConnectionList from './ConnectionList';

interface ConnectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConnectionSelected?: (connectionId: string) => void;
}

const ConnectionModal: React.FC<ConnectionModalProps> = ({ isOpen, onClose, onConnectionSelected }) => {
  const [activeTab, setActiveTab] = useState<'add' | 'manage'>('add');
  const [connections, setConnections] = useState<Connection[]>([]);

  useEffect(() => {
    if (isOpen) {
      loadConnections();
    }
  }, [isOpen]);

  const loadConnections = async () => {
    try {
      const conns = await apiService.getConnections();
      setConnections(conns);
    } catch (err) {
      console.error('Failed to load connections:', err);
    }
  };

  const handleConnectionCreated = (connectionId: string) => {
    loadConnections();
    setActiveTab('manage');
    if (onConnectionSelected) {
      onConnectionSelected(connectionId);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b" style={{ borderColor: 'var(--color-border-muted)' }}>
          <h2 className="text-2xl font-semibold" style={{ color: 'var(--color-text-dark)' }}>
            Manage Connections
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b" style={{ borderColor: 'var(--color-border-muted)' }}>
          <button
            onClick={() => setActiveTab('add')}
            className={`flex-1 px-6 py-3 text-sm font-medium transition ${
              activeTab === 'add'
                ? 'border-b-2 text-gray-900'
                : 'text-gray-500 hover:text-gray-700'
            }`}
            style={activeTab === 'add' ? { borderBottomColor: 'var(--color-accent-green)' } : {}}
          >
            Add Connection
          </button>
          <button
            onClick={() => setActiveTab('manage')}
            className={`flex-1 px-6 py-3 text-sm font-medium transition ${
              activeTab === 'manage'
                ? 'border-b-2 text-gray-900'
                : 'text-gray-500 hover:text-gray-700'
            }`}
            style={activeTab === 'manage' ? { borderBottomColor: 'var(--color-accent-green)' } : {}}
          >
            Manage Connections ({connections.length})
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'add' ? (
            <ProviderConnectForm
              onSuccess={handleConnectionCreated}
              onCancel={onClose}
            />
          ) : (
            <ConnectionList
              connections={connections}
              onRefresh={loadConnections}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default ConnectionModal;

