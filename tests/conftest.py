"""Tests-level conftest. Project root is added to ``sys.path`` by the
project-root conftest, so tests can simply ``import card_linker.core`` etc.

We also expose ``tests/`` itself on ``sys.path`` so suites can share the
``_aqt_stub`` helper without resorting to relative imports (the suites
are loaded by pytest as top-level modules, not as a package).
"""
import sys
from pathlib import Path

_TESTS_DIR = str(Path(__file__).resolve().parent)
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)
