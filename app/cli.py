import argparse
from pathlib import Path

from app.config import WORKSPACE_DIR
from app.ingestion.extract import safe_extract
from app.ingestion.indexer import index_repo
from app.qa import answer

p = argparse.ArgumentParser()
sub = p.add_subparsers(dest="cmd", required=True)

i = sub.add_parser("index")
i.add_argument("zip_path")
i.add_argument("repo_id")

a = sub.add_parser("ask")
a.add_argument("repo_id")
a.add_argument("question")

args = p.parse_args()

if args.cmd == "index":
    root = safe_extract(args.zip_path, Path(WORKSPACE_DIR) / args.repo_id)
    n = index_repo(args.repo_id, root)
    print(f"Indexed {n} chunks")
else:
    text, hits = answer(args.repo_id, args.question)
    print(text)
    print("\nSources retrieved:")
    for h in hits:
        print(f"  {h['file_path']}:{h['start_line']}-{h['end_line']}  rrf_score={h['rrf_score']}")