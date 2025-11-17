/**
 * File upload component with drag-and-drop support
 */

import { useState, useRef } from 'react';
import { apiService } from '../api';
import type { UploadResponse, UploadedFile } from '../types';

interface FileUploadProps {
  onUploadSuccess: (response: UploadResponse) => void;
  uploadedFiles: UploadedFile[];
  onFileSelectionToggle: (documentId: string) => void;
  connectionId?: string | null;
  mongodbUri?: string;
}

const FileUpload: React.FC<FileUploadProps> = ({ onUploadSuccess, uploadedFiles, onFileSelectionToggle, connectionId, mongodbUri }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleFile = async (file: File) => {
    setError('');
    setSuccess('');
    setIsUploading(true);

    try {
      const response = await apiService.uploadFile(file, connectionId || undefined, mongodbUri);
      setSuccess(`Successfully uploaded: ${response.file_name} (${response.total_chunks} chunks)`);
      onUploadSuccess(response);
      
      // Clear success message after 5 seconds
      setTimeout(() => setSuccess(''), 5000);
    } catch (err: any) {
      const errorMessage = err.response?.data?.error || err.message || 'Upload failed';
      setError(errorMessage);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div>
      <h2 className="text-lg font-semibold text-mongodb-darkGray mb-4">
        Upload Documents
      </h2>
      
      <div
        className={`
          border-2 border-dashed rounded-lg p-4 text-center cursor-pointer
          transition-all duration-200
          ${isDragging 
            ? 'border-mongodb-green bg-green-50' 
            : 'border-gray-300 hover:border-mongodb-green hover:bg-gray-50'
          }
          ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={!isUploading ? handleClick : undefined}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".pdf,.txt,.docx,.md"
          onChange={handleFileSelect}
          disabled={isUploading}
        />
        
        {isUploading ? (
          <div className="flex flex-col items-center">
            <div className="spinner mb-4"></div>
            <p className="text-mongodb-slate">Uploading and processing...</p>
          </div>
        ) : (
          <div>
            <svg
              className="mx-auto h-12 w-12 text-mongodb-slate mb-4"
              stroke="currentColor"
              fill="none"
              viewBox="0 0 48 48"
              aria-hidden="true"
            >
              <path
                d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <p className="text-mongodb-darkGray font-medium mb-2">
              Drop files here or click to browse
            </p>
            <p className="text-sm text-mongodb-slate">
              Supported: PDF, TXT, DOCX, MD (Max 10MB)
            </p>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-4 p-4 bg-red-50 border-l-4 border-red-500 rounded-r-md">
          <p className="text-red-700 font-medium">Error: {error}</p>
        </div>
      )}

      {success && (
        <div className="mt-4 p-4 bg-green-50 border-l-4 border-mongodb-green rounded-r-md">
          <p className="text-mongodb-darkGreen font-medium">{success}</p>
        </div>
      )}

      {/* Uploaded Files List with Selection */}
      {uploadedFiles.length > 0 && (
        <div className="mt-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-mongodb-darkGray">
              Files ({uploadedFiles.length})
            </h3>
            <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
              {uploadedFiles.filter(f => f.selectedForIndex).length} selected
            </span>
          </div>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {uploadedFiles.map((file) => (
              <div 
                key={file.document_id}
                className={`p-3 bg-white border rounded-lg hover:shadow-sm transition-all ${
                  file.selectedForIndex ? 'border-2' : ''
                }`}
                style={{ 
                  borderColor: file.selectedForIndex 
                    ? 'var(--color-accent-green)' 
                    : 'var(--color-border-muted)',
                  backgroundColor: file.selectedForIndex ? '#f0fdf4' : 'white'
                }}
              >
                <div className="flex items-start space-x-2">
                  <input
                    type="checkbox"
                    checked={file.selectedForIndex}
                    onChange={() => onFileSelectionToggle(file.document_id)}
                    className="h-4 w-4 rounded cursor-pointer mt-1"
                    style={{ 
                      accentColor: 'var(--color-accent-green)',
                      borderColor: 'var(--color-border-muted)'
                    }}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-1 mb-1">
                      <svg className="h-4 w-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" style={{ color: 'var(--color-text-muted)' }}>
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <span className="font-medium text-sm truncate" style={{ color: 'var(--color-text-dark)' }}>
                        {file.file_name}
                      </span>
                    </div>
                    <div className="text-xs mt-1" style={{ color: 'var(--color-text-muted)' }}>
                      <div className="flex items-center space-x-3">
                        <span>{file.total_chunks} chunks</span>
                        {file.selectedForIndex && (
                          <span className="text-xs px-1.5 py-0.5 rounded" style={{ 
                            backgroundColor: 'var(--color-accent-green)', 
                            color: 'white'
                          }}>
                            Active
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default FileUpload;

