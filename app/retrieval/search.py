from app.ingestion.indexer import get_collection, get_model


def search_code(repo_id: str, query: str, k: int = 6):
    col = get_collection(repo_id)
    q = get_model().encode([query]).tolist()
    res = col.query(query_embeddings=q, n_results=k)
    hits = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        hits.append({**meta, "content": doc, "score": round(1 - dist, 3)})
    return hits