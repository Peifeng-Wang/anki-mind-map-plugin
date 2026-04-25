from pathlib import Path

def pytest_ignore_collect(collection_path, config):
    """Prevent pytest from treating the project root __init__.py as a package."""
    if collection_path.name == "__init__.py":
        root_init = Path(__file__).resolve().parent.parent / "__init__.py"
        if collection_path.resolve() == root_init.resolve():
            return True
    return None
