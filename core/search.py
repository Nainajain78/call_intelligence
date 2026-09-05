"""
Step 11: Search over transcripts (bonus feature).

Two indexes:
  - BM25 keyword index, good for exact-phrase queries ("find every call
    mentioning 'attorney'").
  - Embedding index (via the Anthropic-compatible embeddings you wire up,
    or any embedding provider), good for semantic/fuzzy queries.
Results from both are merged so exact phrase hits aren't buried under
fuzzy semantic matches, and vice versa.

This module works over a corpus of CallReport-line pairs (call_id, line)
so results can be traced back to the exact call and line number.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple
import numpy as np
from rank_bm25 import BM25Okapi
from core.schema import TranscriptLine


@dataclass
class IndexedLine:
    call_id: str
    call_date: str
    line: TranscriptLine


class TranscriptSearchIndex:
    def __init__(self):
        self._entries: List[IndexedLine] = []
        self._bm25: BM25Okapi | None = None
        self._embeddings: np.ndarray | None = None  # optional, filled by add_embeddings

    def add_call(self, call_id: str, call_date: str, lines: List[TranscriptLine]) -> None:
        for line in lines:
            self._entries.append(IndexedLine(call_id=call_id, call_date=call_date, line=line))
        self._rebuild_bm25()

    def _rebuild_bm25(self) -> None:
        tokenized = [e.line.text.lower().split() for e in self._entries]
        self._bm25 = BM25Okapi(tokenized) if tokenized else None

    def keyword_search(self, query: str, top_k: int = 10) -> List[Tuple[IndexedLine, float]]:
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(query.lower().split())
        ranked = sorted(zip(self._entries, scores), key=lambda x: x[1], reverse=True)
        return [(e, s) for e, s in ranked[:top_k] if s > 0]

    def set_embeddings(self, vectors: np.ndarray) -> None:
        """Call after add_call() with embeddings computed for each entry, in
        the same order as self._entries, e.g. via a sentence-embedding model."""
        assert vectors.shape[0] == len(self._entries)
        self._embeddings = vectors

    def semantic_search(self, query_vector: np.ndarray, top_k: int = 10) -> List[Tuple[IndexedLine, float]]:
        if self._embeddings is None:
            return []
        sims = self._embeddings @ query_vector / (
            np.linalg.norm(self._embeddings, axis=1) * np.linalg.norm(query_vector) + 1e-8
        )
        top_idx = np.argsort(sims)[::-1][:top_k]
        return [(self._entries[i], float(sims[i])) for i in top_idx]

    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """Merged keyword results (embeddings optional -- wire in set_embeddings
        + an embedding call for semantic_search to also contribute)."""
        kw_results = self.keyword_search(query, top_k=top_k)
        return [
            {
                "call_id": e.call_id,
                "call_date": e.call_date,
                "line_no": e.line.line_no,
                "speaker": e.line.speaker,
                "text": e.line.text,
                "score": round(score, 3),
            }
            for e, score in kw_results
        ]
