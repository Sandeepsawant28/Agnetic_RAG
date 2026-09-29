import json
from app.retrieval.search import search_code
from app.retrieval.hybrid import hybrid_search

queries = json.loads(open("evals/queries.json").read())

def hit_rate(search_fn, repo_id="demo"):
    hits_found = 0
    for q in queries:
        results = search_fn(repo_id, q["question"], k=6)
        files = [r["file_path"] for r in results]
        if any(q["expected_file_substring"] in f for f in files):
            hits_found += 1
    return hits_found / len(queries)

print(f"Vector-only hit rate: {hit_rate(search_code):.0%}")
print(f"Hybrid hit rate:      {hit_rate(hybrid_search):.0%}")