## Known limitation: filename-referencing queries under-retrieve

Query: "What does the structures.py file define?"
Result: retrieved only the module docstring header chunk, missed the
CaseInsensitiveDict class chunk in the same file (ranked outside top 6).

Query: "What does the CaseInsensitiveDict class do?"
Result: retrieved the correct chunk at rank 1.

Root cause: neither vector similarity nor BM25 term overlap strongly
connects a bare filename reference to unrelated identifier names inside
that file. Both retrieval methods rank on content similarity to the
query, not file-level containment.

Possible fixes (not yet implemented):
- Detect filename mentions in the query and add a metadata filter
  (retrieve all chunks from that file) as a fallback path
- Add a reranking step using a cross-encoder model
- Chunk-level summarization: generate a short per-file summary
  chunk that vector search can match against "what does X file do"
  style questions