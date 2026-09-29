import json
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.retrieval.search import search_code


def _tokenize(text: str):
    return re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text.lower())


def _load_chunks(repo_id: str):
    path = Path("data/bm25") / f"{repo_id}.json"
    return json.loads(path.read_text())


def bm25_search(repo_id: str, query: str, k: int = 10):
    chunks = _load_chunks(repo_id)
    corpus = [_tokenize(c["content"] + " " + c["symbol"] + " " + c["file_path"]) for c in chunks]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(_tokenize(query))
    ranked = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)[:k]
    return [chunks[i] for i in ranked]


def _key(hit: dict) -> str:
    return f"{hit['file_path']}:{hit['start_line']}-{hit['end_line']}"


def hybrid_search(repo_id: str, query: str, k: int = 6, k_rrf: int = 60):
    vector_hits = search_code(repo_id, query, k=10)
    keyword_hits = bm25_search(repo_id, query, k=10)

    rrf_scores = {}
    all_hits = {}

    for rank, hit in enumerate(vector_hits):
        key = _key(hit)
        rrf_scores[key] = rrf_scores.get(key, 0) + 1 / (k_rrf + rank + 1)
        all_hits[key] = hit

    for rank, hit in enumerate(keyword_hits):
        key = _key(hit)
        rrf_scores[key] = rrf_scores.get(key, 0) + 1 / (k_rrf + rank + 1)
        all_hits.setdefault(key, hit)

    ranked_keys = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:k]
    return [{**all_hits[key], "rrf_score": round(rrf_scores[key], 4)} for key in ranked_keys]