from pathlib import Path
from typing import Dict, List, Tuple

import faiss
import numpy as np
import pandas as pd


class FaissStore:
    def __init__(self, index_path: Path, metadata_path: Path, dimension: int = 1536):
        if dimension != 1536:
            raise ValueError("Titan embedding dimension must be 1536")

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
        return self.index.ntotal

    def load_if_exists(self) -> bool:
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
            missing = [col for col in self.metadata_columns if col not in self.metadata_df.columns]
            if missing:
                raise ValueError(f"Metadata parquet missing columns: {missing}")
            loaded = True

        return loaded

    def add_embeddings(self, embeddings: List[List[float]]) -> Tuple[int, int]:
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
        if len(clauses) != len(embeddings):
            raise ValueError("clauses and embeddings must have the same length")

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

        new_df = pd.DataFrame.from_records(records, columns=self.metadata_columns)
        self.metadata_df = pd.concat([self.metadata_df, new_df], ignore_index=True)
        return start_id, end_id

    def search(self, query_embedding: List[float], k: int = 5):
        query = np.asarray([query_embedding], dtype=np.float32)
        if query.ndim != 2 or query.shape[1] != self.dimension:
            raise ValueError(
                f"Invalid query embedding shape: {query.shape}, expected (1, {self.dimension})"
            )
        distances, indices = self.index.search(query, k)
        return distances[0].tolist(), indices[0].tolist()

    def get_metadata_by_id(self, vector_id: int) -> Dict:
        if vector_id < 0:
            return {}

        row = self.metadata_df.loc[self.metadata_df["id"] == vector_id]
        if row.empty:
            return {}
        return row.iloc[0].to_dict()

    def save_local(self):
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))
        self.metadata_df.to_parquet(self.metadata_path, index=False)
