import zipfile
from pathlib import Path

MAX_FILES = 5000
MAX_TOTAL_BYTES = 200 * 1024 * 1024  # 200 MB


def safe_extract(zip_path: str, dest: str) -> Path:
    dest_path = Path(dest).resolve()
    dest_path.mkdir(parents=True, exist_ok=True)
    total = 0
    with zipfile.ZipFile(zip_path) as zf:
        members = zf.infolist()
        if len(members) > MAX_FILES:
            raise ValueError("Archive has too many files")
        for m in members:
            target = (dest_path / m.filename).resolve()
            if not target.is_relative_to(dest_path):
                raise ValueError(f"Unsafe path in archive: {m.filename}")
            total += m.file_size
            if total > MAX_TOTAL_BYTES:
                raise ValueError("Archive too large when extracted")
        zf.extractall(dest_path)
    return dest_path