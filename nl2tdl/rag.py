"""Utilities for loading retrieval documents used in prompting workflows."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List


RAG_ROOT = Path(__file__).resolve().parent.parent / "rag_documents"

MANUFACTURER_PARSING_DOCS = {
    "doosan": [
        "doosan_jobfile_syntax.md",
        "doosan_robotics_instructions.md",
        "TDLset2doosan_mapping.md",
    ],
    "hyundai": [
        "hyundai_jobfile_syntax.md",
        "hyundai_robotics_instructions.md",
        "TDLset2hyundai_mapping.md",
    ],
}

MANUFACTURER_TDL_DOCS = {
    "doosan": [
        "TDLset.md",
        "TDLset2doosan_mapping.md",
    ],
    "hyundai": [
        "TDLset.md",
        "TDLset2hyundai_mapping.md",
    ],
}


def _read_documents(documents: Iterable[str]) -> List[str]:
    """Return the existing document contents for the provided filenames."""

    contents: List[str] = []
    for name in documents:
        path = RAG_ROOT / name
        if path.exists():
            contents.append(path.read_text(encoding="utf-8"))
    return contents


def get_parsing_instructions(manufacturer: str | None = None) -> str:
    """Load job-file parsing instructions for the specified manufacturer."""

    if manufacturer:
        manufacturer = manufacturer.lower()
    docs = MANUFACTURER_PARSING_DOCS.get(manufacturer or "", [])

    contents = _read_documents(docs)
    if not contents:
        # Fallback: include every markdown file to ensure broad coverage
        contents = _read_documents(sorted(p.name for p in RAG_ROOT.glob("*.md")))
    return "\n\n".join(contents).strip()


def get_tdl_syntax_reference(manufacturer: str | None = None) -> str:
    """Load the TDL syntax reference tailored for the manufacturer."""

    docs = ["TDLset.md"]
    if manufacturer:
        manufacturer = manufacturer.lower()
        docs.extend(MANUFACTURER_TDL_DOCS.get(manufacturer, []))

    contents = _read_documents(docs)
    if not contents:
        contents = _read_documents(sorted(p.name for p in RAG_ROOT.glob("*.md")))
    return "\n\n".join(dict.fromkeys(contents)).strip()
