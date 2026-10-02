import re
import shutil
import tempfile
import warnings
from pathlib import Path

# httpbin-style repos contain invalid escape sequences; silence the parser noise
warnings.filterwarnings("ignore", category=SyntaxWarning)

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import WORKSPACE_DIR
from app.ingestion.extract import safe_extract
from app.ingestion.indexer import index_repo
from app.qa import answer  # importing here loads the embedding model once, at startup

app = FastAPI(title="RepoPilot")

REPO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
MAX_ZIP_BYTES = 100 * 1024 * 1024  # 100 MB


class AskBody(BaseModel):
    repo_id: str
    question: str


def check_repo_id(repo_id: str) -> str:
    # repo_id becomes a folder name, so keep it to safe characters
    if not REPO_ID_RE.match(repo_id):
        raise HTTPException(400, "repo_id may only use letters, numbers, - and _ (max 40).")
    return repo_id


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/repos")
def repos():
    root = Path(WORKSPACE_DIR)
    if not root.exists():
        return {"repos": []}
    return {"repos": sorted(p.name for p in root.iterdir() if p.is_dir())}


@app.post("/api/ingest")
def ingest(repo_id: str = Form(...), file: UploadFile = File(...)):
    check_repo_id(repo_id)
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(400, "Upload a .zip file.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        size = 0
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_ZIP_BYTES:
                raise HTTPException(413, "Zip is larger than 100 MB.")
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        root = safe_extract(tmp_path, Path(WORKSPACE_DIR) / repo_id)
        n = index_repo(repo_id, root)
    except Exception as e:
        raise HTTPException(400, f"Indexing failed: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return {"repo_id": repo_id, "chunks": n}


@app.post("/api/ask")
def ask(body: AskBody):
    check_repo_id(body.repo_id)
    if not body.question.strip():
        raise HTTPException(400, "Question is empty.")
    try:
        text, hits = answer(body.repo_id, body.question)
    except Exception as e:
        raise HTTPException(500, f"Could not answer: {e}")

    return {
        "answer": text,
        "sources": [
            {
                "file_path": h["file_path"],
                "start_line": h["start_line"],
                "end_line": h["end_line"],
                "symbol": h.get("symbol"),
                "language": h.get("language"),
                "content": h.get("content", ""),
                "rrf_score": h.get("rrf_score"),
            }
            for h in hits
        ],
    }


# Serve the frontend from the same server (no CORS needed). Keep this LAST.
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")