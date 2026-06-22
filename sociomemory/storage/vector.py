from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from sociomemory.storage.paths import storage_key

logger = logging.getLogger(__name__)


class VectorIndex(Protocol):
    def add(self, node_id: str, embedding: np.ndarray) -> None: ...
    def search(self, query_embedding: np.ndarray, top_k: int = 10) -> list[tuple[str, float]]: ...
    def save(self) -> None: ...
    def delete(self) -> None: ...

    @property
    def size(self) -> int: ...


class NullVectorIndex:
    """No-op vector index used when the optional FAISS dependency is unavailable."""

    def add(self, node_id: str, embedding: np.ndarray) -> None:
        return None

    def search(self, query_embedding: np.ndarray, top_k: int = 10) -> list[tuple[str, float]]:
        return []

    def save(self) -> None:
        return None

    def delete(self) -> None:
        return None

    @property
    def size(self) -> int:
        return 0


class FaissIndex:
    def __init__(self, child_id: str, dim: int = 768, data_dir: str = "~/.sociomemory/faiss"):
        self.child_id = child_id
        self.dim = dim
        self.data_dir = Path(data_dir).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._index: Any = None
        self._faiss: Any = None
        self._id_map: list[str] = []
        self._load_or_init()

    def _load_or_init(self) -> None:
        try:
            import faiss

            self._faiss = faiss
        except ImportError:
            raise ImportError("faiss-cpu is required: pip install faiss-cpu")

        index_path = self._index_path()
        map_path = self._map_path()

        if index_path.exists() and map_path.exists():
            self._index = self._faiss.read_index(str(index_path))
            with open(map_path) as f:
                self._id_map = json.load(f)
        else:
            self._index = self._faiss.IndexFlatIP(self.dim)

    def _index_path(self) -> Path:
        return self.data_dir / f"{storage_key(self.child_id)}.faiss"

    def _map_path(self) -> Path:
        return self.data_dir / f"{storage_key(self.child_id)}.map.json"

    def add(self, node_id: str, embedding: np.ndarray) -> None:
        vec = embedding.astype(np.float32).reshape(1, -1)
        self._faiss.normalize_L2(vec)
        self._index.add(vec)
        self._id_map.append(node_id)

    def search(self, query_embedding: np.ndarray, top_k: int = 10) -> list[tuple[str, float]]:
        if self._index.ntotal == 0:
            return []
        vec = query_embedding.astype(np.float32).reshape(1, -1)
        self._faiss.normalize_L2(vec)
        k = min(top_k, self._index.ntotal)
        scores, indices = self._index.search(vec, k)
        return [
            (self._id_map[int(i)], float(scores[0][j]))
            for j, i in enumerate(indices[0])
            if 0 <= int(i) < len(self._id_map)
        ]

    def save(self) -> None:
        self._faiss.write_index(self._index, str(self._index_path()))
        with open(self._map_path(), "w") as f:
            json.dump(self._id_map, f)

    def delete(self) -> None:
        for p in [self._index_path(), self._map_path()]:
            if p.exists():
                p.unlink()
        self._index = self._faiss.IndexFlatIP(self.dim)
        self._id_map = []

    @property
    def size(self) -> int:
        return len(self._id_map)
