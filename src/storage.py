"""One small storage layer for the daily job and the web app.

All state lives as JSON (and one .npy file) under the paths of the data contract
(docs/data_contract.md). In Azure the files live in a Blob Storage container; on a
laptop they live in data/store/. Both look the same to the rest of the code:

    store = get_store()
    store.write_json("runs/2026-11-07T10-00-00Z.json", {...})
    store.read_json("scored/ncdhhs/latest.json", default=None)

Pick the backend with environment variables:
    STORAGE_CONN       Azure Storage connection string  -> Blob backend (container STORAGE_CONTAINER, default ffm-data)
    (unset)            -> local folder STORE_DIR (default data/store)

Writes that several people can make at once (staff decisions, labels) use
`update_json`, which retries on a conflicting write instead of losing one.
"""

import io
import json
import os
import time
from pathlib import Path

import config

CONTAINER = os.getenv("STORAGE_CONTAINER", "ffm-data")


class ConflictError(Exception):
    pass


class LocalStore:
    kind = "local"

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _p(self, path: str) -> Path:
        p = (self.root / path).resolve()
        if self.root.resolve() not in p.parents and p != self.root.resolve():
            raise ValueError(f"path escapes the store: {path}")
        return p

    def read_bytes(self, path: str) -> bytes | None:
        p = self._p(path)
        return p.read_bytes() if p.exists() else None

    def write_bytes(self, path: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        p = self._p(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, p)

    def version(self, path: str) -> str | None:
        p = self._p(path)
        return str(p.stat().st_mtime_ns) if p.exists() else None

    def write_if_version(self, path: str, data: bytes, version: str | None) -> None:
        if self.version(path) != version:
            raise ConflictError(path)
        self.write_bytes(path, data)

    def list(self, prefix: str) -> list[str]:
        base = self._p(prefix) if prefix else self.root
        if not base.exists():
            return []
        files = [base] if base.is_file() else [f for f in base.rglob("*") if f.is_file() and not f.name.endswith(".tmp")]
        return sorted(f.relative_to(self.root).as_posix() for f in files)

    def describe(self) -> str:
        return f"local folder {self.root}"


class BlobStore:
    kind = "azure-blob"

    def __init__(self, conn: str, container: str):
        from azure.storage.blob import BlobServiceClient
        self.svc = BlobServiceClient.from_connection_string(conn)
        self.container = self.svc.get_container_client(container)
        self.container_name = container
        try:
            self.container.create_container()
        except Exception:
            pass  # already exists (or no permission to create; reads will say so)

    def read_bytes(self, path: str) -> bytes | None:
        from azure.core.exceptions import ResourceNotFoundError
        try:
            return self.container.get_blob_client(path).download_blob().readall()
        except ResourceNotFoundError:
            return None

    def write_bytes(self, path: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        from azure.storage.blob import ContentSettings
        self.container.get_blob_client(path).upload_blob(
            data, overwrite=True, content_settings=ContentSettings(content_type=content_type))

    def version(self, path: str) -> str | None:
        from azure.core.exceptions import ResourceNotFoundError
        try:
            return self.container.get_blob_client(path).get_blob_properties().etag
        except ResourceNotFoundError:
            return None

    def write_if_version(self, path: str, data: bytes, version: str | None) -> None:
        from azure.core import MatchConditions
        from azure.core.exceptions import ResourceExistsError, ResourceModifiedError
        blob = self.container.get_blob_client(path)
        try:
            if version is None:
                blob.upload_blob(data, overwrite=False)
            else:
                blob.upload_blob(data, overwrite=True, etag=version, match_condition=MatchConditions.IfNotModified)
        except (ResourceExistsError, ResourceModifiedError) as e:
            raise ConflictError(path) from e

    def list(self, prefix: str) -> list[str]:
        return sorted(b.name for b in self.container.list_blobs(name_starts_with=prefix))

    def describe(self) -> str:
        return f"Azure Blob container {self.container_name}"


class Store:
    """JSON helpers on top of a byte backend."""

    def __init__(self, backend):
        self.b = backend
        self.kind = backend.kind

    def read_json(self, path: str, default=None):
        raw = self.b.read_bytes(path)
        return default if raw is None else json.loads(raw.decode("utf-8"))

    def write_json(self, path: str, obj, indent: int | None = None) -> None:
        data = json.dumps(obj, ensure_ascii=False, indent=indent, default=str).encode("utf-8")
        self.b.write_bytes(path, data, "application/json")

    def update_json(self, path: str, fn, default, retries: int = 8):
        """Read-modify-write that never silently loses a concurrent write."""
        for attempt in range(retries):
            version = self.b.version(path)
            raw = self.b.read_bytes(path)
            current = default if raw is None else json.loads(raw.decode("utf-8"))
            new = fn(current)
            data = json.dumps(new, ensure_ascii=False, default=str).encode("utf-8")
            try:
                self.b.write_if_version(path, data, version)
                return new
            except ConflictError:
                time.sleep(0.1 * (attempt + 1))
        raise ConflictError(f"could not update {path} after {retries} tries")

    def read_npy(self, path: str):
        import numpy as np
        raw = self.b.read_bytes(path)
        return None if raw is None else np.load(io.BytesIO(raw), allow_pickle=False)

    def write_npy(self, path: str, array) -> None:
        import numpy as np
        buf = io.BytesIO()
        np.save(buf, array, allow_pickle=False)
        self.b.write_bytes(path, buf.getvalue())

    def version(self, path: str) -> str | None:
        return self.b.version(path)

    def list(self, prefix: str) -> list[str]:
        return self.b.list(prefix)

    def describe(self) -> str:
        return self.b.describe()


_STORE = None


def get_store() -> Store:
    global _STORE
    if _STORE is None:
        conn = os.getenv("STORAGE_CONN", "").strip()
        if conn:
            _STORE = Store(BlobStore(conn, CONTAINER))
        else:
            _STORE = Store(LocalStore(Path(os.getenv("STORE_DIR", config.DATA / "store"))))
    return _STORE


def set_store(store: Store | None) -> None:
    """Tests point the app and the job at a temporary store."""
    global _STORE
    _STORE = store
