import chromadb
from pathlib import Path
from sentence_transformers import SentenceTransformer
import json
from pathlib import Path as PathLib

from app.config import CHROMA_DIR, EMBED_MODEL
from app.ingestion.chunker import LANGS, chunk_file, iter_source_files

_model = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def get_collection(repo_id: str):
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_or_create_collection(repo_id, metadata={"hnsw:space": "cosine"})


def index_repo(repo_id: str, root: Path) -> int:
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        client.delete_collection(repo_id)   # re-index from scratch
    except Exception:
        pass
    col = get_collection(repo_id)

    chunks = []
    for f in iter_source_files(root):
        text = f.read_text(errors="ignore")
        rel = str(f.relative_to(root)).replace("\\", "/")
        chunks += chunk_file(text, rel, LANGS[f.suffix])

    save_chunks_for_bm25(repo_id, chunks)

    # Put path + symbol in the embedded text so "user creation route" can match file names
    # Put path + symbol in the embedded text so "user creation route" can match file names
    texts = [f"{c.file_path} {c.symbol}\n{c.content}" for c in chunks]
    vectors = get_model().encode(texts, batch_size=32, show_progress_bar=True).tolist()

    B = 500
    for i in range(0, len(chunks), B):
        part = chunks[i:i + B]
        col.add(
            ids=[f"{repo_id}:{i + j}" for j in range(len(part))],
            documents=[c.content for c in part],
            embeddings=vectors[i:i + B],
            metadatas=[{"file_path": c.file_path, "language": c.language,
                        "symbol": c.symbol, "start_line": c.start_line,
                        "end_line": c.end_line} for c in part],
        )
    return len(chunks)

def save_chunks_for_bm25(repo_id: str, chunks):
    out_dir = PathLib("data/bm25")
    out_dir.mkdir(parents=True, exist_ok=True)
    records = [{"file_path": c.file_path, "language": c.language, "symbol": c.symbol,
                "start_line": c.start_line, "end_line": c.end_line, "content": c.content}
               for c in chunks]
    (out_dir / f"{repo_id}.json").write_text(json.dumps(records))