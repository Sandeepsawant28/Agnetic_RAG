import ast
from dataclasses import dataclass
from pathlib import Path

IGNORE_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__",
               "dist", "build", ".idea", ".vscode"}
LANGS = {".py": "python", ".js": "javascript", ".ts": "typescript",
         ".java": "java", ".go": "go", ".md": "markdown",
         ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml"}
MAX_CHUNK_LINES = 120


@dataclass
class Chunk:
    file_path: str
    language: str
    symbol: str
    start_line: int
    end_line: int
    content: str


def iter_source_files(root: Path):
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix not in LANGS:
            continue
        if set(p.relative_to(root).parts) & IGNORE_DIRS:
            continue
        yield p


def chunk_lines(lines, rel, lang, symbol="<block>", offset=0, size=60, overlap=10):
    chunks, i = [], 0
    while i < len(lines):
        part = lines[i:i + size]
        chunks.append(Chunk(rel, lang, symbol, offset + i + 1,
                            offset + i + len(part), "\n".join(part)))
        if i + size >= len(lines):
            break
        i += size - overlap
    return chunks


def chunk_python(text, rel):
    lines = text.splitlines()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return chunk_lines(lines, rel, "python")

    chunks, first_def = [], None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            end = node.end_lineno
            first_def = start if first_def is None else first_def
            seg = lines[start - 1:end]
            if len(seg) > MAX_CHUNK_LINES:
                chunks += chunk_lines(seg, rel, "python", node.name, offset=start - 1)
            else:
                chunks.append(Chunk(rel, "python", node.name, start, end, "\n".join(seg)))

    header_end = (first_def - 1) if first_def else len(lines)
    if header_end > 0 and "\n".join(lines[:header_end]).strip():
        chunks.append(Chunk(rel, "python", "<module>", 1, header_end,
                            "\n".join(lines[:header_end])))
    return chunks


def chunk_file(text, rel, lang):
    if lang == "python":
        return chunk_python(text, rel)
    return chunk_lines(text.splitlines(), rel, lang)