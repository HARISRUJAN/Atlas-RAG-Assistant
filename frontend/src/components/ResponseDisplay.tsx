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
      <div className="card">
        <div className="flex flex-col items-center py-8">
          <div className="spinner mb-4"></div>
          <p className="text-mongodb-slate">Searching and generating answer...</p>
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
    <div className="space-y-6">
      {/* Answer Section */}
      <div className="card">
        <h3 className="text-lg font-semibold text-mongodb-darkGray mb-3 flex items-center">
          <svg
            className="h-5 w-5 mr-2 text-mongodb-green"
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
          Answer
        </h3>
        
        {/* Best Match - Simple and Clean */}
        {bestMatch && (
          <div className="mb-4 pb-3 border-b" style={{ borderColor: 'var(--color-border-muted)' }}>
            <div className="flex items-center mb-2">
              <span className="text-xs font-medium" style={{ color: 'var(--color-accent-green)' }}>
                Best Match
              </span>
              <span className="text-xs ml-2" style={{ color: 'var(--color-text-muted)' }}>
                • {bestMatch.file_name} (Lines {bestMatch.line_start}-{bestMatch.line_end})
              </span>
            </div>
          </div>
        )}
        
        <div className="prose max-w-none">
          <p className="text-mongodb-mediumGray leading-relaxed whitespace-pre-wrap">
            {response.answer}
          </p>
        </div>
      </div>

      {/* Sources Section - Top Source Only */}
      {topSource && (
        <div className="card">
          <h3 className="text-lg font-semibold text-mongodb-darkGray mb-4 flex items-center">
            <svg
              className="h-5 w-5 mr-2 text-mongodb-green"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
              />
            </svg>
            Source
          </h3>
          <div>
            <SourceReference 
              source={topSource} 
              index={0}
              isTopMatch={true}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default ResponseDisplay;
