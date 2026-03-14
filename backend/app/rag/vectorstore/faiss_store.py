# backend/app/rag/vectorstore/faiss_store.py
"""
FAISS vector store for semantic search.
Extracted from rag-system/vectorstore/faiss_store.py
"""

from pathlib import Path
from typing import Dict, List, Tuple

import faiss
import numpy as np
import pandas as pd


class FaissStore:
    """
    FAISS-based vector store for efficient similarity search.

    Manages a FAISS index alongside metadata stored in parquet format.
    """

    def __init__(self, index_path: Path, metadata_path: Path, dimension: int = 1536):
        """
        Initialize FAISS store.

        Args:
            index_path: Path to FAISS index file
            metadata_path: Path to metadata parquet file
            dimension: Embedding dimension (default 1536 for Titan)
        """
        if dimension <= 0:
            raise ValueError("Embedding dimension must be a positive integer")

        self.index_path = index_path
        self.metadata_path = metadata_path
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)
        self.metadata_columns = [
            "id",
            "insurer",
            "policy_name",
            "clause_id",
            "page",
            "section",
            "text",
            "source_pdf",
        ]
        self.metadata_df = pd.DataFrame(columns=self.metadata_columns)

    @property
    def ntotal(self) -> int:
        """Return total number of vectors in the index."""
        return self.index.ntotal

    def load_if_exists(self) -> bool:
        """
        Load existing index and metadata if available.

        Returns:
            True if any data was loaded, False otherwise
        """
        loaded = False
        if self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            if self.index.d != self.dimension:
                raise ValueError(
                    f"FAISS index dimension mismatch: {self.index.d}, expected {self.dimension}"
                )
            loaded = True

        if self.metadata_path.exists():
            self.metadata_df = pd.read_parquet(self.metadata_path)
            missing = [
                col for col in self.metadata_columns if col not in self.metadata_df.columns]
            if missing:
                raise ValueError(
                    f"Metadata parquet missing columns: {missing}")
            loaded = True

        return loaded

    def add_embeddings(self, embeddings: List[List[float]]) -> Tuple[int, int]:
        """
        Add embeddings to the index.

        Args:
            embeddings: List of embedding vectors

        Returns:
            Tuple of (start_id, end_id) for added vectors
        """
        vectors = np.asarray(embeddings, dtype=np.float32)

        if vectors.ndim != 2 or vectors.shape[1] != self.dimension:
            raise ValueError(
                f"Invalid embedding shape: {vectors.shape}, expected (*, {self.dimension})"
            )

        start_id = self.ntotal
        self.index.add(vectors)
        end_id = self.ntotal
        return start_id, end_id

    def add_clauses(self, clauses: List[Dict], embeddings: List[List[float]]) -> Tuple[int, int]:
        """
        Add clauses with their embeddings to the store.

        Args:
            clauses: List of clause dictionaries with metadata
            embeddings: Corresponding embedding vectors

        Returns:
            Tuple of (start_id, end_id) for added vectors
        """
        if len(clauses) != len(embeddings):
            raise ValueError(
                "clauses and embeddings must have the same length")

        start_id, end_id = self.add_embeddings(embeddings)
        records: List[Dict] = []
        for offset, clause in enumerate(clauses):
            vector_id = start_id + offset
            records.append(
                {
                    "id": vector_id,
                    "insurer": clause.get("insurer", "Unknown"),
                    "policy_name": clause.get("policy_name", "Unknown Policy"),
                    "clause_id": clause.get("clause_id", f"clause-{vector_id}"),
                    "page": clause.get("page"),
                    "section": clause.get("section", "General"),
                    "text": clause.get("text", ""),
                    "source_pdf": clause.get("source_pdf", ""),
                }
            )

        new_df = pd.DataFrame.from_records(
            records, columns=self.metadata_columns)
        self.metadata_df = pd.concat(
            [self.metadata_df, new_df], ignore_index=True)
        return start_id, end_id

    def search(self, query_embedding: List[float], k: int = 5) -> Tuple[List[float], List[int]]:
        """
        Search for similar vectors.

        Args:
            query_embedding: Query vector
            k: Number of results to return

        Returns:
            Tuple of (distances, indices)
        """
        query = np.asarray([query_embedding], dtype=np.float32)
        if query.ndim != 2 or query.shape[1] != self.dimension:
            raise ValueError(
                f"Invalid query embedding shape: {query.shape}, expected (1, {self.dimension})"
            )
        distances, indices = self.index.search(query, k)
        return distances[0].tolist(), indices[0].tolist()

    def get_metadata_by_id(self, vector_id: int) -> Dict:
        """
        Get metadata for a specific vector ID.

        Args:
            vector_id: Vector index

        Returns:
            Metadata dictionary or empty dict if not found
        """
        if vector_id < 0:
            return {}

        row = self.metadata_df.loc[self.metadata_df["id"] == vector_id]
        if row.empty:
            return {}
        return row.iloc[0].to_dict()

    def save_local(self):
        """Save index and metadata to local files."""
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))
        self.metadata_df.to_parquet(self.metadata_path, index=False)
