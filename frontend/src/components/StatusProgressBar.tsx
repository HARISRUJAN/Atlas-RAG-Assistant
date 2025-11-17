/**
 * Status progress bar component showing query processing stages
 * Professional design with white/green color scheme
 */

import React from 'react';

interface StatusProgressBarProps {
  status: 'idle' | 'initializing' | 'mongodb-retriever' | 'generating-answer' | 'complete';
}

const StatusProgressBar: React.FC<StatusProgressBarProps> = ({ status }) => {
  if (status === 'idle') {
    return null;
  }

  const stages = [
    { 
      key: 'initializing', 
      label: 'Initializing Query',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      )
    },
    { 
      key: 'mongodb-retriever', 
      label: 'MongoDB Retriever',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      )
    },
    { 
      key: 'generating-answer', 
      label: 'Generating Answer',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
        </svg>
      )
    },
    { 
      key: 'complete', 
      label: 'Complete',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
        </svg>
      )
    }
  ];

  const currentIndex = stages.findIndex(s => s.key === status);
  const isComplete = status === 'complete';

  return (
    <div className="w-full bg-white border-b shadow-sm" style={{ borderColor: 'var(--color-border-muted)' }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2">
        <div className="flex items-center justify-center">
          {stages.map((stage, index) => {
            const isActive = index === currentIndex && !isComplete;
            const isCompleted = index < currentIndex || isComplete;
            
            // Determine if the connecting line should be green
            const lineIsGreen = isCompleted;

            return (
              <React.Fragment key={stage.key}>
                <div className="flex flex-col items-center">
                  {/* Stage Circle */}
                  <div
                    className={`
                      flex items-center justify-center
                      w-8 h-8 rounded-full
                      border-2 transition-all duration-300
                      ${isActive || isCompleted
                        ? 'bg-green-500 border-green-500'
                        : 'bg-white border-gray-300'
                      }
                    `}
                    style={isActive || isCompleted ? { backgroundColor: 'var(--color-accent-green)', borderColor: 'var(--color-accent-green)' } : {}}
                  >
                    {isActive && !isComplete ? (
                      <div className="spinner" style={{ width: '14px', height: '14px', borderTopColor: 'white' }}></div>
                    ) : isCompleted ? (
                      <div style={{ color: 'white' }}>
                        {stage.key === 'complete' ? (
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                          </svg>
                        ) : (
                          <div style={{ color: 'white' }}>
                            {stage.icon}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div style={{ color: '#9CA3AF' }}>
                        {stage.icon}
                      </div>
                    )}
                  </div>
                  
                  {/* Stage Label */}
                  <span
                    className={`
                      mt-1 text-[10px] font-medium transition-colors duration-300
                      ${isActive || isCompleted
                        ? 'text-green-600'
                        : 'text-gray-400'
                      }
                    `}
                    style={isActive || isCompleted ? { color: 'var(--color-accent-green)' } : {}}
                  >
                    {stage.label}
                  </span>
                </div>
                
                {/* Connecting Line */}
                {index < stages.length - 1 && (
                  <div className="flex-1 mx-2 mt-[-16px]">
                    <div
                      className={`
                        h-[2px] transition-all duration-500
                        ${lineIsGreen
                          ? 'bg-green-500'
                          : 'bg-gray-300'
                        }
                      `}
                      style={lineIsGreen ? { backgroundColor: 'var(--color-accent-green)' } : {}}
                    />
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default StatusProgressBar;
