from pathlib import Path
import pickle
from typing import Dict, List, Tuple

import faiss
import numpy as np


class FaissStore:
    def __init__(self, index_path: Path, metadata_path: Path, dimension: int = 1536):
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(dimension)
        self.metadata: List[Dict] = []

    @property
    def ntotal(self) -> int:
        return self.index.ntotal

    def load_if_exists(self) -> bool:
        loaded = False
        if self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            loaded = True

        if self.metadata_path.exists():
            with self.metadata_path.open("rb") as file:
                self.metadata = pickle.load(file)
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
        self.metadata.extend(clauses)
        return start_id, end_id

    def search(self, query_embedding: List[float], k: int = 5):
        query = np.asarray([query_embedding], dtype=np.float32)
        distances, indices = self.index.search(query, k)
        return distances[0].tolist(), indices[0].tolist()

    def save_local(self):
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))
        with self.metadata_path.open("wb") as file:
            pickle.dump(self.metadata, file)
