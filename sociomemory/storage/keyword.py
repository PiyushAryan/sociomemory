from __future__ import annotations

import json
import re
from pathlib import Path

import bm25s

from sociomemory.storage.paths import storage_key

TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


class BM25Index:
    """Persistent per-child BM25 index with lazy rebuilding after writes."""

    def __init__(self, child_id: str, data_dir: str = "~/.sociomemory/keyword"):
        self.child_id = child_id
        self.data_dir = Path(data_dir).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._docs: dict[str, str] = {}
        self._order: list[str] = []
        self._retriever = None
        self._dirty = True
        self._load()

    def add(self, node_id: str, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        self._docs[node_id] = text
        self._dirty = True

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        query = (query or "").strip()
        if not query or not self._docs:
            return []
        if self._dirty or self._retriever is None:
            self._build()
        if not self._order:
            return []
        assert self._retriever is not None

        query_tokens = bm25s.tokenize(query, stopwords="en", show_progress=False)
        k = min(top_k, len(self._order))
        results, scores = self._retriever.retrieve(query_tokens, k=k, show_progress=False)

        hits: list[tuple[str, float]] = []
        for idx, score in zip(results[0].tolist(), scores[0].tolist()):
            if score > 0 and 0 <= idx < len(self._order):
                hits.append((self._order[idx], float(score)))
        return hits

    def _build(self) -> None:
        self._order = list(self._docs.keys())
        if not self._order:
            self._retriever = None
            self._dirty = False
            return
        corpus = [self._docs[node_id] for node_id in self._order]
        corpus_tokens = bm25s.tokenize(corpus, stopwords="en", show_progress=False)
        retriever = bm25s.BM25()
        retriever.index(corpus_tokens, show_progress=False)
        self._retriever = retriever
        self._dirty = False

    def save(self) -> None:
        self._index_path().write_text(json.dumps({"docs": self._docs}))

    def delete(self) -> None:
        path = self._index_path()
        if path.exists():
            path.unlink()
        self._docs = {}
        self._order = []
        self._retriever = None
        self._dirty = True

    @property
    def size(self) -> int:
        return len(self._docs)

    def _load(self) -> None:
        path = self._index_path()
        if not path.exists():
            return
        try:
            payload = json.loads(path.read_text())
        except json.JSONDecodeError:
            return
        docs = payload.get("docs", {})
        if docs and all(isinstance(value, dict) for value in docs.values()):
            # Back-compat: the old pure-Python format stored term->count maps.
            # Reconstruct approximate text so pre-existing indexes keep working.
            self._docs = {
                str(node_id): " ".join(
                    " ".join([str(term)] * int(count)) for term, count in counts.items()
                )
                for node_id, counts in docs.items()
            }
        else:
            self._docs = {str(node_id): str(text) for node_id, text in docs.items()}
        self._dirty = True

    def _index_path(self) -> Path:
        return self.data_dir / f"{storage_key(self.child_id)}.bm25.json"


def tokenize(text: str) -> list[str]:
    """Tokenize text for callers that relied on the original public helper."""
    return [token.lower() for token in TOKEN_RE.findall(text)]
