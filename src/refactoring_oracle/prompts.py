"""The frozen prompt for the API arms, and the skill files for the skill arm.

Everything an arm sees is hashed into the artifact's meta, so a result can be
tied to the exact words that produced it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from refactoring_oracle.case import REPO_ROOT, Case
from refactoring_oracle.collateral import _files

SKILLS_DIR = REPO_ROOT / "skills"

SYSTEM_PROMPT = (
    "You are performing one named refactoring on a small Python project.\n\n"
    "You will receive the project's files and an instruction that names the target interface "
    "exactly. Apply exactly that refactoring and nothing else: keep behavior identical, do not "
    "touch files or functions the instruction does not mention, do not add imports beyond what "
    "the refactoring needs, do not reformat or reorder unrelated code, and do not add comments "
    "or docstrings that were not there.\n\n"
    "Return every file you changed, complete, through the write_files tool. Do not return files "
    "you did not change. Do not explain."
)

TOOL_NAME = "write_files"
TOOL: dict[str, Any] = {
    "name": TOOL_NAME,
    "description": "Write the complete new contents of each file the refactoring changed.",
    "input_schema": {
        "type": "object",
        "properties": {
            "files": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string",
                                 "description": "Path relative to the project root."},
                        "content": {"type": "string", "description": "The full file contents."},
                    },
                    "required": ["path", "content"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["files"],
        "additionalProperties": False,
    },
}


def project_listing(case: Case) -> str:
    parts = []
    for rel, path in sorted(_files(case.before_dir).items()):
        parts.append(f"### path: {rel}\n```python\n{path.read_text(encoding='utf-8')}```")
    return "\n\n".join(parts)


def user_message(case: Case) -> str:
    return f"Instruction:\n{case.instruction}\n\nFiles:\n\n{project_listing(case)}"


def skill_path(refactoring: str) -> Path:
    return SKILLS_DIR / f"{refactoring}.md"


def load_skill(refactoring: str) -> str:
    return skill_path(refactoring).read_text(encoding="utf-8")


def system_prompt(skill: str | None) -> str:
    if skill is None:
        return SYSTEM_PROMPT
    return f"{SYSTEM_PROMPT}\n\nA skill describing this refactoring follows. Use it.\n\n{skill}"


def prompt_sha256() -> str:
    payload = {
        "system": SYSTEM_PROMPT,
        "tool": TOOL,
        "user_template": "Instruction:\n{instruction}\n\nFiles:\n\n{listing}",
    }
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def skills_sha256() -> str:
    h = hashlib.sha256()
    for p in sorted(SKILLS_DIR.glob("*.md")):
        h.update(p.name.encode("utf-8"))
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()
