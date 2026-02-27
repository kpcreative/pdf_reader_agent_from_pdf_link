"""Custom PDF reader that preserves page numbers in metadata."""

import tempfile
import httpx
from pathlib import Path
from typing import List, Dict, Any
from phi.document import Document
from phi.document.reader.pdf import PDFReader


class PDFUrlReaderWithPages:
    """
    Downloads PDF from URL and reads it with page number tracking.
    """
    
    def __init__(self, chunk_size: int = 1000, chunk: bool = True):
        self.chunk_size = chunk_size
        self.chunk = chunk
    
    def read(self, url: str) -> List[Document]:
        """Download PDF from URL and extract text with page numbers."""
        # Download PDF to temp file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            response = httpx.get(url, follow_redirects=True, timeout=60)
            response.raise_for_status()
            tmp_file.write(response.content)
            tmp_path = tmp_file.name
        
        try:
            documents = self._extract_pages_with_numbers(tmp_path, url)
            return documents
        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)
    
    def _extract_pages_with_numbers(self, pdf_path: str, source_url: str) -> List[Document]:
        """Extract text from each page with page number metadata."""
        try:
            import pypdf
        except ImportError:
            raise ImportError("pypdf is required. Install with: pip install pypdf")
        
        documents = []
        
        with open(pdf_path, "rb") as f:
            pdf_reader = pypdf.PdfReader(f)
            total_pages = len(pdf_reader.pages)
            
            for page_num, page in enumerate(pdf_reader.pages, start=1):
                text = page.extract_text() or ""
                
                if not text.strip():
                    continue
                
                # Create metadata with page info
                meta_data = {
                    "page_number": page_num,
                    "total_pages": total_pages,
                    "source_url": source_url,
                    "source_type": "pdf",
                }
                
                if self.chunk:
                    # Split page into chunks but preserve page number
                    chunks = self._chunk_text(text, page_num, total_pages, source_url)
                    documents.extend(chunks)
                else:
                    documents.append(Document(
                        content=text,
                        meta_data=meta_data
                    ))
        
        return documents
    
    def _chunk_text(self, text: str, page_num: int, total_pages: int, source_url: str) -> List[Document]:
        """Split text into chunks while preserving page number metadata."""
        chunks = []
        
        # Simple chunking by character count with overlap
        words = text.split()
        current_chunk = []
        current_length = 0
        chunk_index = 0
        
        for word in words:
            current_chunk.append(word)
            current_length += len(word) + 1
            
            if current_length >= self.chunk_size:
                chunk_text = " ".join(current_chunk)
                chunks.append(Document(
                    content=chunk_text,
                    meta_data={
                        "page_number": page_num,
                        "total_pages": total_pages,
                        "source_url": source_url,
                        "source_type": "pdf",
                        "chunk_index": chunk_index,
                    }
                ))
                # Keep last few words for overlap
                overlap_words = current_chunk[-20:] if len(current_chunk) > 20 else []
                current_chunk = overlap_words
                current_length = sum(len(w) + 1 for w in current_chunk)
                chunk_index += 1
        
        # Don't forget remaining text
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append(Document(
                content=chunk_text,
                meta_data={
                    "page_number": page_num,
                    "total_pages": total_pages,
                    "source_url": source_url,
                    "source_type": "pdf",
                    "chunk_index": chunk_index,
                }
            ))
        
        return chunks


def load_pdf_with_pages(url: str) -> List[Document]:
    """
    Load a PDF from URL and return documents with page numbers.
    """
    reader = PDFUrlReaderWithPages(chunk_size=1000)
    return reader.read(url)