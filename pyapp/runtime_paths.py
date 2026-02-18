from __future__ import annotations

import sys
from pathlib import Path


def _unique_existing(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    seen: set[str] = set()
    for p in paths:
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        if p.exists():
            out.append(p)
    return out


def resource_search_roots() -> list[Path]:
    roots: list[Path] = []

    module_dir = Path(__file__).resolve().parent
    project_root = module_dir.parent
    roots.extend([project_root, module_dir])

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(Path(meipass))

    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        # Common app bundle / extracted runtime locations.
        roots.extend([
            exe.parent,
            exe.parent.parent,
            exe.parent.parent.parent,
            exe.parent.parent.parent.parent,
            exe.parent.parent.parent.parent.parent,
        ])

    return _unique_existing(roots)


def find_resource(*relative_paths: str) -> Path | None:
    roots = resource_search_roots()

    for rel in relative_paths:
        p = Path(rel)
        if p.is_absolute() and p.exists():
            return p

    for root in roots:
        for rel in relative_paths:
            candidate = root / rel
            if candidate.exists():
                return candidate

    return None
