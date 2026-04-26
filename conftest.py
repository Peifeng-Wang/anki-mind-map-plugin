"""Project-root conftest used only for pytest.

The project root contains an ``__init__.py`` because Anki loads this directory
as a package. Pytest treats the same directory as a Python package and tries
to import that file for every test collected underneath it. The ``__init__``
guards itself against running without ``aqt`` available, so importing it under
pytest is safe — but we still need the project root on ``sys.path`` so tests
can do absolute imports like ``import card_linker.core``.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
