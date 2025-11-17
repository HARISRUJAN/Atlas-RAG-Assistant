/**
 * Provider connection form component (adapted for modal)
 */

import { useState, useMemo } from 'react';
import { apiService } from '../api';
import type { Provider, Scope } from '../types';

const PROVIDERS: { id: Provider; label: string }[] = [
  { id: 'mongo', label: 'MongoDB' },
  { id: 'redis', label: 'Redis' },
  { id: 'qdrant', label: 'Qdrant' },
  { id: 'pinecone', label: 'Pinecone' },
];

const SCOPE_OPTIONS: { id: Scope; label: string }[] = [
  { id: 'list.indexes', label: 'List indexes' },
  { id: 'read.metadata', label: 'Read metadata' },
  { id: 'read.vectors', label: 'Read vectors' },
  { id: 'write.vectors', label: 'Write vectors (optional)' },
];

const PLACEHOLDERS: Record<Provider, string> = {
  mongo: 'mongodb://user:pass@host:27017/db?authSource=admin',
  redis: 'redis://:password@host:6379/0',
  qdrant: 'https://qdrant.example.com',
  pinecone: 'https://controller.YOUR-REGION.pinecone.io',
};

const HelpText: Record<Provider, React.ReactNode> = {
  mongo: (
    <ul className="list-disc pl-5 text-xs text-gray-600 space-y-1">
      <li>Requires MongoDB 7.0+ with vector indexes for $vectorSearch.</li>
      <li>URI may include authSource and TLS params.</li>
    </ul>
  ),
  redis: (
    <ul className="list-disc pl-5 text-xs text-gray-600 space-y-1">
      <li>Requires Redis Stack/RediSearch with VECTOR fields (HNSW).</li>
      <li>Use redis://:password@host:port/db format.</li>
    </ul>
  ),
  qdrant: (
    <ul className="list-disc pl-5 text-xs text-gray-600 space-y-1">
      <li>Self-hosted or managed Qdrant endpoint URL.</li>
      <li>Provide API key if required by your deployment.</li>
    </ul>
  ),
  pinecone: (
    <ul className="list-disc pl-5 text-xs text-gray-600 space-y-1">
      <li>Controller URL for your Pinecone project/region.</li>
      <li>Provide API key; index/namespace selection will follow after connect.</li>
    </ul>
  ),
};

interface ProviderConnectFormProps {
  onSuccess?: (connectionId: string) => void;
  onCancel?: () => void;
}

const ProviderConnectForm: React.FC<ProviderConnectFormProps> = ({ onSuccess, onCancel }) => {
  const [provider, setProvider] = useState<Provider>('mongo');
  const [connectionUri, setConnectionUri] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [scopes, setScopes] = useState<Record<Scope, boolean>>({
    'list.indexes': true,
    'read.metadata': true,
    'read.vectors': false,
    'write.vectors': false,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const needApiKey = provider === 'qdrant' || provider === 'pinecone';
  const scopeList = useMemo(
    () => SCOPE_OPTIONS.map(s => ({ ...s, checked: scopes[s.id] })),
    [scopes]
  );
  const selectedScopes = useMemo(
    () => Object.entries(scopes).filter(([_, v]) => v).map(([k]) => k) as Scope[],
    [scopes]
  );

  function toggleScope(id: Scope) {
    setScopes(prev => ({ ...prev, [id]: !prev[id] }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e && e.preventDefault();
    setBusy(true);
    setError(null);

    try {
      // 1) Create connection
      const createRes = await apiService.createConnection({
        provider,
        display_name: displayName || `${provider.toUpperCase()} Connection`,
        uri: connectionUri,
        api_key: needApiKey ? apiKey : undefined,
      });

      // 2) Consent scopes
      await apiService.updateConnectionScopes(createRes.connection_id, selectedScopes);

      if (onSuccess) {
        onSuccess(createRes.connection_id);
      }
    } catch (err: any) {
      setError(err?.response?.data?.error || err?.message || 'Something went wrong');
    } finally {
      setBusy(false);
    }
  }

  const invalid = !connectionUri || (needApiKey && !apiKey);

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Provider selector */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Provider</label>
        <div className="grid grid-cols-2 gap-2">
          {PROVIDERS.map(p => (
            <button
              key={p.id}
              type="button"
              onClick={() => setProvider(p.id)}
              className={`px-3 py-2 rounded-lg border text-sm transition ${
                provider === p.id
                  ? 'bg-gray-900 text-white border-gray-900'
                  : 'bg-white text-gray-800 border-gray-300 hover:border-gray-400'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Display name */}
      <div>
        <label className="block text-sm font-medium text-gray-700">Display name</label>
        <input
          type="text"
          placeholder="e.g., Prod Mongo, Team Search Redis"
          className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
          value={displayName}
          onChange={e => setDisplayName(e.target.value)}
        />
      </div>

      {/* Connection URI */}
      <div>
        <label className="block text-sm font-medium text-gray-700">Connection</label>
        <input
          type="text"
          placeholder={PLACEHOLDERS[provider]}
          className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-xs focus:outline-none focus:ring-2 focus:ring-gray-900"
          value={connectionUri}
          onChange={e => setConnectionUri(e.target.value)}
        />
        <div className="mt-1">{HelpText[provider]}</div>
      </div>

      {/* API key if needed */}
      {needApiKey && (
        <div>
          <label className="block text-sm font-medium text-gray-700">API Key</label>
          <input
            type="password"
            placeholder="Paste provider API key"
            className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-xs focus:outline-none focus:ring-2 focus:ring-gray-900"
            value={apiKey}
            onChange={e => setApiKey(e.target.value)}
          />
          <p className="text-xs text-gray-500 mt-1">Stored securely in your server-side vault.</p>
        </div>
      )}

      {/* Scopes */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Permissions</label>
        <div className="grid grid-cols-2 gap-2">
          {scopeList.map(s => (
            <label key={s.id} className="flex items-center gap-2 p-2 rounded-lg border border-gray-200 hover:border-gray-300">
              <input
                type="checkbox"
                className="rounded"
                checked={!!s.checked}
                onChange={() => toggleScope(s.id)}
              />
              <span className="text-xs">{s.label}</span>
            </label>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-2">You can grant additional scopes later.</p>
      </div>

      {/* Error message */}
      {error && (
        <div className="p-3 rounded-lg bg-red-50 text-red-700 border border-red-200 text-sm">
          {error}
        </div>
      )}

      {/* Submit buttons */}
      <div className="flex gap-3">
        <button
          type="submit"
          disabled={busy || invalid}
          className={`flex-1 px-4 py-2 rounded-lg text-white ${
            busy || invalid ? 'bg-gray-400 cursor-not-allowed' : 'bg-gray-900 hover:bg-black'
          }`}
        >
          {busy ? 'Connecting…' : 'Connect'}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 rounded-lg border border-gray-300 hover:bg-gray-50"
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  );
};

export default ProviderConnectForm;

