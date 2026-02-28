# backend/app/ingestion/clause_splitter.py
"""
Insurance policy clause splitting and chunking.
"""

import re
import logging
from typing import List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PolicyClause:
    """Represents a policy clause chunk."""
    clause_id: str
    section: str
    title: str
    content: str
    page_number: int
    chunk_index: int
    metadata: Dict[str, Any]


class ClauseSplitter:
    """
    Splits insurance policy documents into semantic chunks.
    Preserves clause structure and hierarchy.
    """

    # Section header patterns
    SECTION_PATTERNS = [
        r"^(?:SECTION|ARTICLE|PART)\s+([IVXLCDM\d]+)[:\.\s]+(.+)$",
        r"^(\d+(?:\.\d+)*)[:\.\s]+(.+)$",
        r"^([A-Z])[:\.\s]+(.+)$",
    ]

    # Clause patterns
    CLAUSE_PATTERNS = [
        r"^(?:Clause|Coverage|Exclusion|Limitation)\s+(\d+(?:\.\d+)*)[:\.\s]*(.*)$",
    ]

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    async def split_document(
        self,
        text: str,
        document_id: str
    ) -> List[PolicyClause]:
        """
        Split policy document into clauses.

        Args:
            text: Full document text
            document_id: Source document identifier

        Returns:
            List of policy clause chunks
        """
        # First, identify sections
        sections = self._identify_sections(text)

        # Split each section into chunks
        clauses = []
        chunk_index = 0

        for section in sections:
            section_chunks = self._chunk_section(section)

            for chunk in section_chunks:
                clause = PolicyClause(
                    clause_id=f"{document_id}_chunk_{chunk_index}",
                    section=section["section_id"],
                    title=section["title"],
                    content=chunk["content"],
                    page_number=section.get("page_number", 0),
                    chunk_index=chunk_index,
                    metadata={
                        "document_id": document_id,
                        "section_title": section["title"],
                        "is_exclusion": self._is_exclusion(chunk["content"]),
                        "is_coverage": self._is_coverage(chunk["content"]),
                        "has_conditions": self._has_conditions(chunk["content"])
                    }
                )
                clauses.append(clause)
                chunk_index += 1

        logger.info(f"Split document into {len(clauses)} clauses")
        return clauses

    def _identify_sections(self, text: str) -> List[Dict[str, Any]]:
        """Identify document sections."""
        sections = []
        current_section = {
            "section_id": "0",
            "title": "Introduction",
            "content": "",
            "page_number": 1
        }

        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for section headers
            is_section = False
            for pattern in self.SECTION_PATTERNS:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    # Save current section
                    if current_section["content"]:
                        sections.append(current_section)

                    # Start new section
                    current_section = {
                        "section_id": match.group(1),
                        "title": match.group(2) if len(match.groups()) > 1 else line,
                        "content": "",
                        "page_number": 1
                    }
                    is_section = True
                    break

            if not is_section:
                current_section["content"] += line + "\n"

        # Add last section
        if current_section["content"]:
            sections.append(current_section)

        return sections

    def _chunk_section(self, section: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunk a section into smaller pieces."""
        content = section["content"]
        chunks = []

        # If content is small enough, return as single chunk
        if len(content) <= self.chunk_size:
            if len(content) >= self.min_chunk_size:
                chunks.append({"content": content})
            return chunks

        # Split by paragraphs first
        paragraphs = content.split("\n\n")
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Check if adding paragraph exceeds chunk size
            if len(current_chunk) + len(para) > self.chunk_size:
                if current_chunk:
                    chunks.append({"content": current_chunk.strip()})

                # Handle large paragraphs
                if len(para) > self.chunk_size:
                    para_chunks = self._split_large_paragraph(para)
                    chunks.extend(para_chunks[:-1])
                    current_chunk = para_chunks[-1]["content"] if para_chunks else ""
                else:
                    current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        # Add remaining content
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            chunks.append({"content": current_chunk.strip()})

        # Add overlap between chunks
        chunks = self._add_overlap(chunks)

        return chunks

    def _split_large_paragraph(self, paragraph: str) -> List[Dict[str, Any]]:
        """Split a large paragraph into smaller chunks."""
        chunks = []
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) > self.chunk_size:
                if current_chunk:
                    chunks.append({"content": current_chunk.strip()})
                current_chunk = sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence

        if current_chunk:
            chunks.append({"content": current_chunk.strip()})

        return chunks

    def _add_overlap(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add overlap between consecutive chunks."""
        if len(chunks) <= 1:
            return chunks

        overlapped_chunks = []

        for i, chunk in enumerate(chunks):
            content = chunk["content"]

            # Add overlap from previous chunk
            if i > 0:
                prev_content = chunks[i - 1]["content"]
                overlap_text = prev_content[-self.chunk_overlap:]
                # Find sentence boundary
                sentence_start = overlap_text.find(". ")
                if sentence_start != -1:
                    overlap_text = overlap_text[sentence_start + 2:]
                content = overlap_text + " " + content

            overlapped_chunks.append({"content": content})

        return overlapped_chunks

    def _is_exclusion(self, text: str) -> bool:
        """Check if chunk contains exclusion language."""
        exclusion_keywords = [
            "exclusion", "excluded", "not covered", "does not cover",
            "will not pay", "not payable", "except", "unless"
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in exclusion_keywords)

    def _is_coverage(self, text: str) -> bool:
        """Check if chunk contains coverage language."""
        coverage_keywords = [
            "coverage", "covered", "we will pay", "benefits include",
            "eligible for", "entitled to", "reimburse"
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in coverage_keywords)

    def _has_conditions(self, text: str) -> bool:
        """Check if chunk contains conditional language."""
        condition_keywords = [
            "if", "when", "provided that", "subject to",
            "condition", "requirement", "must", "shall"
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in condition_keywords)
