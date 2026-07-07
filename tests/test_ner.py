from __future__ import annotations

from types import SimpleNamespace

from sociomemory.pipeline import ner
from sociomemory.pipeline.ner import Candidate, candidates_from_doc, spacy_candidates


def _ent(text: str, label: str, start: int, end: int) -> SimpleNamespace:
    return SimpleNamespace(text=text, label_=label, start_char=start, end_char=end)


def test_candidates_from_doc_collects_ner_and_quoted():
    text = 'We live in Koramangala near "Forum Mall"'
    doc = SimpleNamespace(text=text, ents=[_ent("Koramangala", "GPE", 11, 22)])
    cands = candidates_from_doc(doc)
    texts = {c.text for c in cands}
    labels = {c.label for c in cands}
    assert "Koramangala" in texts
    assert "Forum Mall" in texts
    assert "GPE" in labels and "QUOTED" in labels


def test_candidates_from_doc_rejects_unaccepted_labels():
    doc = SimpleNamespace(text="at 3pm", ents=[_ent("3pm", "TIME", 3, 6)])
    assert candidates_from_doc(doc) == []


def test_spacy_candidates_empty_when_model_unavailable(monkeypatch):
    monkeypatch.setattr(ner, "_load_nlp", lambda: None)
    assert spacy_candidates("I live in Koramangala") == []


def test_spacy_candidates_empty_for_blank_text():
    assert spacy_candidates("   ") == []
