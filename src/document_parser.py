"""Document parser and text chunker for user-uploaded retail operations files.

Supports PDF, DOCX, TXT, and Markdown files (vendor contracts, invoices, SOPs, catalogues).
Provides robust text extraction, page tracking, and semantic chunking.
"""
import re
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

import pypdf
import docx

logger = logging.getLogger("document_parser")

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit


class DocumentParser:
    """Parses and chunks multi-format documents for RAG retrieval."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 80):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def is_supported(self, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext in SUPPORTED_EXTENSIONS

    def parse_and_chunk(self, file_path: Path, original_filename: str, doc_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Parses a file and returns semantic chunks with rich metadata."""
        doc_id = doc_id or str(uuid.uuid4())[:8]
        ext = Path(original_filename).suffix.lower()

        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file format '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")

        file_size = file_path.stat().st_size
        if file_size > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File size exceeds 10MB limit ({round(file_size / (1024*1024), 2)} MB)")

        if ext in {".txt", ".md"}:
            return self._parse_text_file(file_path, original_filename, doc_id, ext)
        elif ext == ".pdf":
            return self._parse_pdf_file(file_path, original_filename, doc_id)
        elif ext == ".docx":
            return self._parse_docx_file(file_path, original_filename, doc_id)
        else:
            raise ValueError(f"Unhandled extension: {ext}")

    def _parse_text_file(self, file_path: Path, filename: str, doc_id: str, ext: str) -> List[Dict[str, Any]]:
        """Extracts text from plain text and markdown files."""
        content = ""
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue

        if not content.strip():
            logger.warning(f"File {filename} is empty or unreadable.")
            return []

        return self._create_chunks(content, filename, doc_id, ext.replace(".", "").upper(), page_number=1)

    def _parse_pdf_file(self, file_path: Path, filename: str, doc_id: str) -> List[Dict[str, Any]]:
        """Extracts text from PDF documents page by page."""
        all_chunks = []
        try:
            reader = pypdf.PdfReader(str(file_path))
            total_pages = len(reader.pages)

            for page_idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    page_chunks = self._create_chunks(
                        text=page_text,
                        filename=filename,
                        doc_id=doc_id,
                        file_type="PDF",
                        page_number=page_idx + 1,
                        start_chunk_idx=len(all_chunks)
                    )
                    all_chunks.extend(page_chunks)

        except Exception as e:
            logger.error(f"Error parsing PDF {filename}: {e}", exc_info=True)
            raise ValueError(f"Could not parse PDF '{filename}': {str(e)}")

        return all_chunks

    def _parse_docx_file(self, file_path: Path, filename: str, doc_id: str) -> List[Dict[str, Any]]:
        """Extracts text from Microsoft Word .docx documents (paragraphs & tables)."""
        all_chunks = []
        try:
            doc = docx.Document(str(file_path))
            full_text_parts = []

            # Extract body paragraphs
            for p in doc.paragraphs:
                txt = p.text.strip()
                if txt:
                    full_text_parts.append(txt)

            # Extract table cells
            for table in doc.tables:
                for row in table.rows:
                    row_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_texts:
                        full_text_parts.append(" | ".join(row_texts))

            full_text = "\n\n".join(full_text_parts)
            if full_text.strip():
                all_chunks = self._create_chunks(
                    text=full_text,
                    filename=filename,
                    doc_id=doc_id,
                    file_type="DOCX",
                    page_number=1
                )
        except Exception as e:
            logger.error(f"Error parsing DOCX {filename}: {e}", exc_info=True)
            raise ValueError(f"Could not parse Word document '{filename}': {str(e)}")

        return all_chunks

    def _create_chunks(
        self,
        text: str,
        filename: str,
        doc_id: str,
        file_type: str,
        page_number: Optional[int] = None,
        start_chunk_idx: int = 0
    ) -> List[Dict[str, Any]]:
        """Splits raw text into overlapping semantic chunks."""
        # Clean whitespace and normalize line breaks
        cleaned = re.sub(r"\r\n|\r", "\n", text)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

        if not cleaned:
            return []

        chunks = []
        paragraphs = cleaned.split("\n\n")
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                current_chunk = f"{current_chunk}\n\n{para}".strip()
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                # If a single paragraph is longer than chunk_size, split by sentences or length
                if len(para) > self.chunk_size:
                    for sub in self._split_long_paragraph(para):
                        chunks.append(sub)
                    current_chunk = ""
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        # Build structured chunk dictionaries
        result = []
        for i, chk in enumerate(chunks):
            idx = start_chunk_idx + i
            result.append({
                "chunk_id": f"{doc_id}_c{idx:03d}",
                "doc_id": doc_id,
                "filename": filename,
                "file_type": file_type,
                "page_number": page_number,
                "chunk_index": idx,
                "text": chk,
                "char_count": len(chk)
            })

        return result

    def _split_long_paragraph(self, text: str) -> List[str]:
        """Splits an oversized paragraph cleanly by sentences or fixed bounds."""
        sentences = re.split(r"(?<=[.?!])\s+", text)
        pieces = []
        curr = ""

        for s in sentences:
            if len(curr) + len(s) + 1 <= self.chunk_size:
                curr = f"{curr} {s}".strip()
            else:
                if curr:
                    pieces.append(curr)
                if len(s) > self.chunk_size:
                    # Hard character split as last resort
                    for start in range(0, len(s), self.chunk_size - self.chunk_overlap):
                        pieces.append(s[start:start + self.chunk_size])
                    curr = ""
                else:
                    curr = s

        if curr:
            pieces.append(curr)

        return pieces
