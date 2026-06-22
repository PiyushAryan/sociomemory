from __future__ import annotations

from sociomemory.storage.keyword import BM25Index, tokenize


def test_tokenize_normalizes_words_and_numbers():
    assert tokenize("Koramangala therapy-center 2BHK") == [
        "koramangala",
        "therapy",
        "center",
        "2bhk",
    ]


def test_bm25_index_ranks_keyword_matches(tmp_path):
    index = BM25Index("child_001", data_dir=str(tmp_path))
    index.add("node-a", "Koramangala occupational therapy center")
    index.add("node-b", "Whitefield school transport")

    results = index.search("therapy in Koramangala", top_k=2)

    assert results[0][0] == "node-a"
    assert len(results) == 1


def test_bm25_index_persists_to_disk(tmp_path):
    first = BM25Index("child_001", data_dir=str(tmp_path))
    first.add("node-a", "Salt Lake autism therapy")
    first.save()

    second = BM25Index("child_001", data_dir=str(tmp_path))

    assert second.size == 1
    assert second.search("autism Salt Lake")[0][0] == "node-a"
