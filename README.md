# Code Q&A: Ask Questions About a Codebase

A retrieval-augmented Q&A tool for source code. Point it at a repository, ask questions in plain English ("where do we generate unique IDs?"), and get an answer grounded in the actual code chunks, with file references.

The project is built as much around **measuring** retrieval quality as around the app itself. Every retrieval change is evaluated against the same question set before it is enabled.

> Replace the `<placeholders>` below with your own details (repo name, commands, model names).

---

## How it works

```
question
   │
   ▼
[optional] query rewriting  ──► turns question words into code vocabulary
   │                            ("unique identifier" → "uuid4 generate")
   ▼
retrieval  (vector / keyword / hybrid)
   │
   ▼
[optional] reranker  (off by default, see Findings)
   │
   ▼
relevance gate  ──► refuses when nothing relevant was found
   │
   ▼
LLM answer, grounded in retrieved chunks
```

**Components**

| Path | Role |
|---|---|
| `app/ingestion/indexer.py` | Chunks a repo, embeds the chunks, stores them in a per-repo vector collection |
| `app/retrieval/search.py` | `search_code(repo_id, query, k)`: vector search, returns chunks with a similarity `score` (`1 - distance`) |
| `app/llm.py` | `chat(messages, temperature)`: thin wrapper over any OpenAI-compatible endpoint |
| `app/config.py` | `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, and optional gate thresholds |
| `evals/run_eval_v2.py` | Retrieval eval harness (recall@k, MRR, per-question-type breakdown) |

---

## Retrieval modes

- **Vector only**: embedding similarity over code chunks.
- **Keyword only**: lexical matching.
- **Hybrid**: vector + keyword, merged with Reciprocal Rank Fusion (RRF).
- **Hybrid + rerank**: hybrid results re-scored by a cross-encoder.

---

## Evaluation

Run on the `sample` repo with 27 scored questions (each question ≈ 3.7 percentage points).

| Mode | recall@1 | recall@3 | recall@6 | MRR |
|---|---|---|---|---|
| vector only | 67% | 89% | 96% | 0.78 |
| keyword only | 41% | 67% | 74% | 0.52 |
| hybrid | 59% | 89% | 93% | 0.74 |
| hybrid + rerank | 52% | 74% | 81% | 0.64 |

Reproduce:

```bash
python -m evals.run_eval_v2 --repo sample --modes vector,hybrid --detail
```

### Findings

- **The reranker hurt, so it is disabled by default.** A general-purpose cross-encoder cut recall@6 from 93% to 81% on code. It scored 100% on exact-name questions but only 12% at rank 1 (50% at rank 6) on concept questions. It was trained on web text, not code.
- **Hybrid did not beat vector-only.** The 67% vs 59% gap at rank 1 is two questions, which could be noise at this sample size. Keyword search alone is weak (74% at rank 6), and mixing it in with equal weight pulls in some irrelevant chunks.
- **RRF and reranker scores can't gate "nothing relevant".** Unanswerable questions scored as high as answerable ones, so no cutoff separated them. `MIN_TOP_SCORE` and `MIN_RERANK_SCORE` are left unset.
- **Most remaining misses are vocabulary mismatches**, where the question's words don't appear in the code ("unique identifier" → `uuid`, "browser" → `user-agent`, "compress" → `gzip`).

### Limitations

- The eval set is small (27 scored questions) and comes from one repo, so results risk overfitting. Next step: grow to ~60 questions across a second repo.
- Differences of one or two questions between modes should not be treated as significant.

---

## Roadmap

These are in progress and **not yet measured** against the table above:

1. **Query rewriting**: the LLM rewrites the question into code vocabulary before searching. Targets the vocabulary-mismatch misses.
2. **Agent loop**: the LLM can search repeatedly, which should help multi-file questions. Uses a plain JSON protocol, so it works with any OpenAI-compatible model without native tool calling.
3. **Score-based relevance gate**: test raw vector similarity (`score` from `search_code`) as the "nothing relevant" signal, since it's a better candidate than RRF or rerank scores.
4. **API + UI wiring** for the agent.

Each feature will only be enabled by default if it improves on this same eval.

---

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure the LLM (any OpenAI-compatible endpoint)
export LLM_API_KEY=<your key>
export LLM_BASE_URL=<endpoint url>
export LLM_MODEL=<model name>

# 3. Index a repository
python -m app.ingestion.indexer --repo <path-or-url> --id <repo_id>   # adjust to your actual CLI

# 4. Run the server
uvicorn app.main:app --reload                                         # adjust to your actual entrypoint
```

## Usage

```python
from app.retrieval.search import search_code

hits = search_code("sample", "where is the unique ID generated?", k=6)
for h in hits:
    print(h["score"], h.get("path"), h["content"][:80])
```

---

## Design notes

- **Measure before enabling.** Retrieval features ship behind flags and are turned on only when the eval supports it.
- **Negative results are documented**, not hidden (see the reranker finding).
- **Provider-agnostic LLM layer**: one `chat()` function over an OpenAI-compatible client.
