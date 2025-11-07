"""Document processing service for file uploads and text extraction."""

import os
import uuid
from datetime import datetime
from typing import List, Tuple
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

# Document loaders
from PyPDF2 import PdfReader
import docx
import markdown

from backend.config import Config
from backend.models.document import DocumentMetadata, DocumentChunk
from backend.utils.chunking import chunk_text_with_line_numbers


class DocumentProcessor:
    """Processes uploaded documents and extracts text content."""
    
    def __init__(self):
        """Initialize document processor."""
        self.upload_folder = Config.UPLOAD_FOLDER
    
    def process_file(self, file: FileStorage) -> Tuple[DocumentMetadata, List[DocumentChunk]]:
        """
        Process uploaded file and return metadata and chunks.
        
        Args:
            file: Uploaded file object
            
        Returns:
            Tuple of (DocumentMetadata, List[DocumentChunk])
        """
        # Generate document ID
        document_id = str(uuid.uuid4())
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        file_path = os.path.join(self.upload_folder, f"{document_id}_{filename}")
        file.save(file_path)
        
        # Extract text based on file type
        try:
            text = self._extract_text(file_path, file_extension)
            
            # Chunk the text with line numbers
            chunks_data = chunk_text_with_line_numbers(text)
            
            # Create document metadata
            file_size = os.path.getsize(file_path)
            metadata = DocumentMetadata(
                document_id=document_id,
                file_name=filename,
                file_type=file_extension,
                file_size=file_size,
                upload_date=datetime.now(),
                total_chunks=len(chunks_data)
            )
            
            # Create document chunks
            chunks = []
            for idx, (chunk_text, line_start, line_end) in enumerate(chunks_data):
                chunk = DocumentChunk(
                    chunk_id=f"{document_id}_chunk_{idx}",
                    document_id=document_id,
                    file_name=filename,
                    chunk_index=idx,
                    content=chunk_text,
                    line_start=line_start,
                    line_end=line_end,
                    metadata={'file_type': file_extension}
                )
                chunks.append(chunk)
            
            return metadata, chunks
            
        finally:
            # Clean up temporary file
            if os.path.exists(file_path):
                os.remove(file_path)
    
    def _extract_text(self, file_path: str, file_extension: str) -> str:
        """
        Extract text from file based on type.
        
        Args:
            file_path: Path to file
            file_extension: File extension
            
        Returns:
            Extracted text content
        """
        if file_extension == 'pdf':
            return self._extract_from_pdf(file_path)
        elif file_extension == 'docx':
            return self._extract_from_docx(file_path)
        elif file_extension == 'txt':
            return self._extract_from_txt(file_path)
        elif file_extension == 'md':
            return self._extract_from_markdown(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file."""
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    
    def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file."""
        doc = docx.Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    
    def _extract_from_txt(self, file_path: str) -> str:
        """Extract text from TXT file."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    def _extract_from_markdown(self, file_path: str) -> str:
        """Extract text from Markdown file."""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            md_content = f.read()
        # Convert markdown to plain text (keep markdown as is, or convert to HTML then strip)
        # For now, just return the raw markdown
        return md_content

