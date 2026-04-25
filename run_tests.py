import os
import subprocess
import sys

root = os.path.dirname(os.path.abspath(__file__))
init_path = os.path.join(root, "__init__.py")
init_backup = os.path.join(root, "_init.py")

# Default test files for the split modules
DEFAULT_TESTS = [
    "tests/test_card_linker.py",
    "tests/test_mindmap_tree_utils.py",
    "tests/test_mindmap_assets.py",
    "tests/test_mindmap_cleanup.py",
    "tests/test_mindmap_sync.py",
    "tests/test_mindmap_maplinks.py",
    "tests/test_mindmap_dialog.py",
]

# Temporarily move root __init__.py to avoid pytest treating the project root
# as a package (directory name contains hyphens, invalid Python package name).
if os.path.exists(init_path):
    os.rename(init_path, init_backup)

try:
    args = [sys.executable, "-m", "pytest"] + DEFAULT_TESTS + ["-v"]
    if len(sys.argv) > 1:
        # If user passes arguments, override default test list
        args = [sys.executable, "-m", "pytest"] + sys.argv[1:] + ["-v"]
    result = subprocess.run(args, cwd=root)
    sys.exit(result.returncode)
finally:
    if os.path.exists(init_backup):
        os.rename(init_backup, init_path)
