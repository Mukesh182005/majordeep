"""Load modules from the official baseline repositories without polluting sys.path.

Both official repositories ship a top-level ``networks`` package, and UnivFD a
generic ``models`` package, so they are imported from file paths under unique
module names instead of being put on ``sys.path``.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


def load_module(name: str, path: Path, package_dir: Path | None = None) -> types.ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    if not path.is_file():
        raise FileNotFoundError(f"Official baseline file not found: {path}")
    locations = [str(package_dir)] if package_dir is not None else None
    spec = importlib.util.spec_from_file_location(name, path, submodule_search_locations=locations)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def stub_text_only_dependency(name: str) -> None:
    """Satisfy an import that only text tokenisation uses (never called for images)."""
    if name in sys.modules or importlib.util.find_spec(name) is not None:
        return

    def _unavailable(*_args, **_kwargs):
        raise RuntimeError(f"'{name}' is stubbed: text tokenisation is not available in image scoring")

    stub = types.ModuleType(name)
    stub.fix_text = _unavailable  # type: ignore[attr-defined]
    sys.modules[name] = stub
