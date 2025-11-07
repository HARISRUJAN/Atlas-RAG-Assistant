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
}

const FileUpload: React.FC<FileUploadProps> = ({ onUploadSuccess, uploadedFiles, onFileSelectionToggle }) => {
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
      const response = await apiService.uploadFile(file);
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
    <div className="card">
      <h2 className="text-2xl font-semibold text-mongodb-darkGray mb-4">
        Upload Documents
      </h2>
      
      <div
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
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
        <div className="mt-6">
          <h3 className="text-lg font-semibold text-mongodb-darkGray mb-3">
            Uploaded Documents ({uploadedFiles.length})
          </h3>
          <div className="space-y-2">
            {uploadedFiles.map((file) => (
              <div 
                key={file.document_id}
                className="flex items-center p-3 bg-white border rounded-lg hover:shadow-md transition-shadow"
                style={{ borderColor: 'var(--color-border-muted)' }}
              >
                <input
                  type="checkbox"
                  checked={file.selectedForIndex}
                  onChange={() => onFileSelectionToggle(file.document_id)}
                  className="h-5 w-5 rounded cursor-pointer"
                  style={{ 
                    accentColor: 'var(--color-accent-green)',
                    borderColor: 'var(--color-border-muted)'
                  }}
                />
                <div className="ml-3 flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-medium" style={{ color: 'var(--color-text-dark)' }}>
                      {file.file_name}
                    </span>
                    <span className="text-xs px-2 py-1 rounded" style={{ 
                      backgroundColor: 'var(--color-accent-green)', 
                      color: 'white'
                    }}>
                      {file.total_chunks} chunks
                    </span>
                  </div>
                  <div className="text-sm mt-1" style={{ color: 'var(--color-text-muted)' }}>
                    {file.selectedForIndex ? (
                      <span className="flex items-center">
                        <svg className="h-4 w-4 mr-1" fill="currentColor" viewBox="0 0 20 20" style={{ color: 'var(--color-accent-green)' }}>
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                        </svg>
                        Included in search
                      </span>
                    ) : (
                      <span>Not included in search</span>
                    )}
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

