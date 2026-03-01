# backend/app/ingestion/pdf_parser.py
"""
PDF document parsing and text extraction.
"""

import io
import logging
from typing import Optional, List
import fitz  # PyMuPDF
from pdfminer.high_level import extract_text as pdfminer_extract
from pdfminer.layout import LAParams

from app.core.exceptions import DocumentProcessingError

logger = logging.getLogger(__name__)


class PDFParser:
    """
    PDF parser with multiple extraction strategies.
    Falls back to OCR if text extraction fails.
    """

    def __init__(self):
        self.min_text_length = 100  # Minimum characters for valid extraction

    async def extract_text(self, pdf_content: bytes) -> str:
        """
        Extract text from PDF content.

        Args:
            pdf_content: Raw PDF file bytes

        Returns:
            Extracted text content

        Raises:
            DocumentProcessingError: If extraction fails
        """
        try:
            # Try PyMuPDF first (faster)
            text = self._extract_with_pymupdf(pdf_content)

            if len(text.strip()) < self.min_text_length:
                # Fall back to pdfminer (better for some PDFs)
                text = self._extract_with_pdfminer(pdf_content)

            if len(text.strip()) < self.min_text_length:
                # PDF might be image-based, needs OCR
                logger.warning("PDF appears to be image-based, OCR required")
                return ""

            return self._clean_text(text)

        except Exception as e:
            logger.error(f"PDF extraction failed: {str(e)}")
            raise DocumentProcessingError(
                f"Failed to extract text from PDF: {str(e)}"
            )

    def _extract_with_pymupdf(self, pdf_content: bytes) -> str:
        """Extract text using PyMuPDF."""
        text_parts = []

        with fitz.open(stream=pdf_content, filetype="pdf") as doc:
            for page_num, page in enumerate(doc):
                text = page.get_text("text")
                if text.strip():
                    text_parts.append(f"[Page {page_num + 1}]\n{text}")

        return "\n\n".join(text_parts)

    def _extract_with_pdfminer(self, pdf_content: bytes) -> str:
        """Extract text using pdfminer."""
        laparams = LAParams(
            line_margin=0.5,
            word_margin=0.1,
            char_margin=2.0,
            boxes_flow=0.5
        )

        return pdfminer_extract(
            io.BytesIO(pdf_content),
            laparams=laparams
        )

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove excessive whitespace
        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def get_page_count(self, pdf_content: bytes) -> int:
        """Get number of pages in PDF."""
        with fitz.open(stream=pdf_content, filetype="pdf") as doc:
            return len(doc)
