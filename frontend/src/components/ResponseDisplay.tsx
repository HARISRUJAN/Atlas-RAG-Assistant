/**
 * Response display component showing answer and sources
 */

import type { QueryResponse } from '../types';
import SourceReference from './SourceReference';

interface ResponseDisplayProps {
  response: QueryResponse | null;
  isLoading: boolean;
}

const ResponseDisplay: React.FC<ResponseDisplayProps> = ({ response, isLoading }) => {
  if (isLoading) {
    return (
      <div className="flex justify-start">
        <div className="max-w-3xl bg-white border rounded-lg p-4 shadow-sm" style={{ borderColor: 'var(--color-border-muted)' }}>
          <div className="flex items-center space-x-2">
            <div className="spinner" style={{ width: '20px', height: '20px' }}></div>
            <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Searching and generating answer...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!response) {
    return (
      <div className="card bg-gray-50 border-dashed">
        <div className="text-center py-8">
          <svg
            className="mx-auto h-12 w-12 text-mongodb-slate mb-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
            />
          </svg>
          <p className="text-mongodb-slate">
            Ask a question to get started
          </p>
        </div>
      </div>
    );
  }

  // Sort sources by relevance score and take only the top source
  const sortedSources = response.sources 
    ? [...response.sources].sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0))
    : [];
  
  const topSource = sortedSources[0];
  const bestMatch = topSource;

  return (
    <div className="space-y-4">
      {!response && !isLoading && (
        <div className="flex flex-col items-center justify-center h-full min-h-[400px]">
          <svg
            className="mx-auto h-16 w-16 mb-4"
            style={{ color: 'var(--color-text-muted)' }}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
            />
          </svg>
          <p className="text-lg" style={{ color: 'var(--color-text-muted)' }}>
            Ask a question to get started
          </p>
        </div>
      )}

      {response && (
        <div className="space-y-4">
          {/* User Query */}
          <div className="flex justify-end">
            <div className="max-w-3xl bg-gray-100 rounded-lg p-4" style={{ backgroundColor: '#f3f4f6' }}>
              <p className="text-sm font-medium mb-1" style={{ color: 'var(--color-text-dark)' }}>
                You asked:
              </p>
              <p className="text-sm" style={{ color: 'var(--color-text-dark)' }}>
                {response.query}
              </p>
            </div>
          </div>

          {/* AI Response */}
          <div className="flex justify-start">
            <div className="max-w-3xl bg-white border rounded-lg p-4 shadow-sm" style={{ borderColor: 'var(--color-border-muted)' }}>
              <div className="flex items-center mb-2">
                <svg
                  className="h-5 w-5 mr-2"
                  style={{ color: 'var(--color-accent-green)' }}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <span className="text-sm font-medium" style={{ color: 'var(--color-text-dark)' }}>
                  Answer
                </span>
                {bestMatch && (
                  <span className="text-xs ml-2 px-2 py-1 rounded" style={{ 
                    backgroundColor: 'var(--color-accent-green)', 
                    color: 'white'
                  }}>
                    {bestMatch.file_name}
                  </span>
                )}
              </div>
              
              <div className="prose max-w-none">
                <p className="text-sm leading-relaxed whitespace-pre-wrap" style={{ color: 'var(--color-text-dark)' }}>
                  {response.answer}
                </p>
              </div>

              {bestMatch && (
                <div className="mt-3 pt-3 border-t text-xs" style={{ borderColor: 'var(--color-border-muted)', color: 'var(--color-text-muted)' }}>
                  Source: {bestMatch.file_name} (Lines {bestMatch.line_start}-{bestMatch.line_end})
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ResponseDisplay;
