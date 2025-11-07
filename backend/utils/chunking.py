"""Text chunking utilities with line number preservation."""

from typing import List, Tuple
from langchain_text_splitters import RecursiveCharacterTextSplitter
from backend.config import Config


def chunk_text_with_line_numbers(
    text: str,
    chunk_size: int = None,
    chunk_overlap: int = None
) -> List[Tuple[str, int, int]]:
    """
    Chunk text while preserving line number information.
    
    Args:
        text: Input text to chunk
        chunk_size: Size of each chunk (default from config)
        chunk_overlap: Overlap between chunks (default from config)
        
    Returns:
        List of tuples (chunk_text, line_start, line_end)
    """
    chunk_size = chunk_size or Config.CHUNK_SIZE
    chunk_overlap = chunk_overlap or Config.CHUNK_OVERLAP
    
    # Split text into lines for line number tracking
    lines = text.split('\n')
    
    # Create text splitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    # Split text into chunks
    chunks = splitter.split_text(text)
    
    # Map chunks to line numbers
    result = []
    current_pos = 0
    
    for chunk in chunks:
        # Find the start position of this chunk in the original text
        chunk_start = text.find(chunk, current_pos)
        if chunk_start == -1:
            # Fallback: chunk might be slightly modified by splitter
            chunk_start = current_pos
        
        chunk_end = chunk_start + len(chunk)
        
        # Calculate line numbers
        text_before_chunk = text[:chunk_start]
        text_including_chunk = text[:chunk_end]
        
        line_start = text_before_chunk.count('\n') + 1
        line_end = text_including_chunk.count('\n') + 1
        
        result.append((chunk, line_start, line_end))
        
        # Move position forward
        current_pos = chunk_start + 1
    
    return result

