/**
 * Source reference display component
 */

import type { SourceReference as SourceReferenceType } from '../types';

interface SourceReferenceProps {
  source: SourceReferenceType;
  index: number;
  isTopMatch?: boolean;
}

const SourceReference: React.FC<SourceReferenceProps> = ({ source, index, isTopMatch = false }) => {
  const scorePercentage = Math.round((source.relevance_score || 0) * 100);
  
  return (
    <div 
      className="p-4 rounded-lg transition-shadow hover:shadow-md"
      style={{ 
        backgroundColor: 'white',
        border: `1px solid ${isTopMatch ? 'var(--color-accent-green)' : 'var(--color-border-muted)'}`,
        borderLeftWidth: isTopMatch ? '4px' : '1px'
      }}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center">
          {isTopMatch && (
            <span className="mr-2 px-2 py-0.5 text-xs font-bold rounded" style={{
              backgroundColor: 'var(--color-accent-green)',
              color: 'white'
            }}>
              #1
            </span>
          )}
          <h4 className="font-semibold" style={{ color: 'var(--color-text-dark)' }}>
            {source.file_name}
          </h4>
        </div>
        
        {/* Similarity Score */}
        <div className="flex items-center">
          <div className="text-right">
            <div className="text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>
              Relevance
            </div>
            <div className="text-sm font-bold" style={{ 
              color: scorePercentage > 70 ? 'var(--color-accent-green)' : 'var(--color-text-muted)'
            }}>
              {scorePercentage}%
            </div>
          </div>
          <div className="ml-2 w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className="h-full rounded-full transition-all"
              style={{ 
                width: `${scorePercentage}%`,
                backgroundColor: 'var(--color-accent-green)'
              }}
            />
          </div>
        </div>
      </div>
      
      <div className="text-sm mb-2" style={{ color: 'var(--color-text-muted)' }}>
        Lines {source.line_start} - {source.line_end}
      </div>
      
      <div className="text-sm leading-relaxed p-3 rounded" style={{ 
        backgroundColor: 'var(--color-bg-primary)',
        color: 'var(--color-text-dark)'
      }}>
        {source.content.substring(0, 200)}
        {source.content.length > 200 && '...'}
      </div>
    </div>
  );
};

export default SourceReference;
