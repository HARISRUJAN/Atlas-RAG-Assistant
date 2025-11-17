/**
 * Provider badge component for displaying provider type
 */

import type { Provider } from '../types';

interface ProviderBadgeProps {
  provider: Provider;
  size?: 'sm' | 'md' | 'lg';
}

const PROVIDER_COLORS: Record<Provider, string> = {
  mongo: '#3FA037', // MongoDB green
  redis: '#DC382D', // Redis red
  qdrant: '#1E88E5', // Qdrant blue
  pinecone: '#FF6B35', // Pinecone orange
};

const PROVIDER_LABELS: Record<Provider, string> = {
  mongo: 'MongoDB',
  redis: 'Redis',
  qdrant: 'Qdrant',
  pinecone: 'Pinecone',
};

const SIZE_CLASSES = {
  sm: 'text-xs px-1.5 py-0.5',
  md: 'text-sm px-2 py-1',
  lg: 'text-base px-3 py-1.5',
};

const ProviderBadge: React.FC<ProviderBadgeProps> = ({ provider, size = 'sm' }) => {
  const color = PROVIDER_COLORS[provider];
  const label = PROVIDER_LABELS[provider];
  const sizeClass = SIZE_CLASSES[size];

  return (
    <span
      className={`inline-flex items-center rounded font-medium ${sizeClass}`}
      style={{
        backgroundColor: `${color}20`,
        color: color,
        border: `1px solid ${color}40`,
      }}
    >
      {label}
    </span>
  );
};

export default ProviderBadge;

