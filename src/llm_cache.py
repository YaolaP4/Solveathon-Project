"""On-disk cache of every model response.

Each response is stored as one JSON file keyed by a hash of (model, prompt version,
exact request). The cache is committed to the repo, so `python src/pipeline.py` can
reproduce the ranking with no API key and no cost. Changing a prompt changes the
hash, so stale answers are never reused by accident.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def request_hash(model: str, prompt_version: str, request) -> str:
    blob = json.dumps({"model": model, "prompt_version": prompt_version, "request": request},
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def prompt_version(*texts: str) -> str:
    """Short hash identifying a prompt template (recorded with every cached answer)."""
    return hashlib.sha256("\n".join(texts).encode("utf-8")).hexdigest()[:12]


class ResponseCache:
    def __init__(self, directory: Path, layer: str):
        self.dir = Path(directory) / layer
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, grant_id: str, key: str) -> Path:
        safe = "".join(c for c in str(grant_id) if c.isalnum() or c in "-_")[:80]
        return self.dir / f"{safe}__{key[:16]}.json"

    def get(self, grant_id: str, key: str):
        p = self._path(grant_id, key)
        if p.exists():
            with open(p, encoding="utf-8") as f:
                return json.load(f)["response"]
        return None

    def put(self, grant_id: str, key: str, model: str, version: str, response) -> None:
        record = {
            "grant_id": grant_id,
            "model": model,
            "prompt_version": version,
            "request_hash": key,
            "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "response": response,
        }
        with open(self._path(grant_id, key), "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=1)
