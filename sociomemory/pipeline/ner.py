from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_MODEL_NAME = "en_core_web_sm"

# spaCy NER labels we treat as socioeconomic-entity candidates. Everything
# else (TIME, CARDINAL, ORDINAL, ...) is ignored.
_ACCEPTED_LABELS = {
    "GPE",
    "LOC",
    "ORG",
    "PERSON",
    "FAC",
    "DATE",
    "MONEY",
    "NORP",
    "LANGUAGE",
}

# Text inside double quotes (straight or curly) — titles, specific names.
# Single quotes/apostrophes are intentionally excluded to avoid matching
# contractions (“don't”, “that's”) as quoted spans.
_QUOTED_RE = re.compile(r'["“”]([^"“”]{2,60})["“”]')

_nlp = None
_load_failed = False
_lock = threading.Lock()


@dataclass(frozen=True)
class Candidate:
    text: str
    label: str  # a spaCy NER label, or "QUOTED"
    start: int
    end: int


def _load_nlp():
    """Lazily load the spaCy model; return the nlp object or None.

    Caches a failure so a missing/broken model is not retried on every call.
    """
    global _nlp, _load_failed
    if _load_failed:
        return None
    if _nlp is not None:
        return _nlp
    with _lock:
        if _nlp is not None:
            return _nlp
        if _load_failed:
            return None
        try:
            import spacy
        except ImportError:
            logger.info("spaCy not installed; skipping NER pre-pass (install sociomemory[nlp])")
            _load_failed = True
            return None
        try:
            _nlp = spacy.load(_MODEL_NAME)
        except Exception as exc:  # model missing or load error
            logger.warning(
                "spaCy model %s unavailable (%s); run: python -m spacy download %s",
                _MODEL_NAME,
                exc,
                _MODEL_NAME,
            )
            _load_failed = True
            return None
    return _nlp


def candidates_from_doc(doc) -> list[Candidate]:
    """Extract entity candidates from a spaCy-like Doc.

    Uses accepted NER entities plus quoted spans. Intentionally lean: no
    proper-noun capitalization heuristics (they fail on code-mixed text).
    """
    seen: set[tuple[int, int]] = set()
    out: list[Candidate] = []
    for ent in getattr(doc, "ents", []):
        if ent.label_ not in _ACCEPTED_LABELS:
            continue
        span = (ent.start_char, ent.end_char)
        if span in seen:
            continue
        seen.add(span)
        out.append(Candidate(text=ent.text, label=ent.label_, start=span[0], end=span[1]))
    text = getattr(doc, "text", "") or ""
    for match in _QUOTED_RE.finditer(text):
        span = (match.start(1), match.end(1))
        if span in seen:
            continue
        seen.add(span)
        out.append(
            Candidate(text=match.group(1).strip(), label="QUOTED", start=span[0], end=span[1])
        )
    return out


def spacy_candidates(text: str) -> list[Candidate]:
    """Return entity candidates for text, or [] if spaCy is unavailable."""
    if not text or not text.strip():
        return []
    nlp = _load_nlp()
    if nlp is None:
        return []
    try:
        doc = nlp(text)
    except Exception as exc:  # pragma: no cover - runtime spaCy error
        logger.warning("spaCy processing failed: %s", exc)
        return []
    return candidates_from_doc(doc)
