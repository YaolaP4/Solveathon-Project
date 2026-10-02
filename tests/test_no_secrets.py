"""Guard: no API key may ever be committed. Scans every file git tracks or is about
to track (including cached model responses) for anything shaped like a key."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY = re.compile(rb"vck_[A-Za-z0-9]{16,}|sk-[A-Za-z0-9]{20,}")


def tracked_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                         cwd=ROOT, capture_output=True, check=True).stdout.decode()
    return [ROOT / f for f in out.splitlines() if f]


def test_env_file_is_ignored():
    r = subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=ROOT)
    assert r.returncode == 0, ".env must be git-ignored"
    assert ROOT / ".env" not in tracked_files()


def test_no_api_key_in_any_committable_file():
    leaks = [str(p.relative_to(ROOT)) for p in tracked_files()
             if p.is_file() and p.stat().st_size < 50_000_000 and KEY.search(p.read_bytes())]
    assert not leaks, f"API-key-shaped strings found in: {leaks}"
