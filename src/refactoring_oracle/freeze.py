"""Freeze the whole cases tree by hash, so no arm ever runs on edited cases."""

from __future__ import annotations

import hashlib
from pathlib import Path

from refactoring_oracle.case import CASES_ROOT, REPO_ROOT
from refactoring_oracle.collateral import _files

HASH_PATH = REPO_ROOT / "cases.sha256"


class FixtureDrift(RuntimeError):
    pass


def tree_sha256(root: Path = CASES_ROOT) -> str:
    h = hashlib.sha256()
    for rel, path in sorted(_files(root).items()):
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(path.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def freeze(root: Path = CASES_ROOT, hash_path: Path = HASH_PATH) -> str:
    digest = tree_sha256(root)
    hash_path.write_text(f"{digest}  {root.name}/\n", encoding="utf-8")
    return digest


def recorded(hash_path: Path = HASH_PATH) -> str | None:
    if not hash_path.exists():
        return None
    return hash_path.read_text(encoding="utf-8").split()[0]


def check_frozen(root: Path = CASES_ROOT, hash_path: Path = HASH_PATH) -> str:
    want = recorded(hash_path)
    have = tree_sha256(root)
    if want is None:
        raise FixtureDrift(f"{hash_path.name} is missing; run ro-freeze first")
    if want != have:
        raise FixtureDrift(
            f"cases/ changed since it was frozen (recorded {want[:12]}, actual {have[:12]}); "
            "re-run ro-freeze deliberately"
        )
    return have
