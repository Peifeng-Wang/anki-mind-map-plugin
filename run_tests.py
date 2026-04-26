import os
import subprocess
import sys

root = os.path.dirname(os.path.abspath(__file__))
init_path = os.path.join(root, "__init__.py")
init_backup = os.path.join(root, "_init.py")

# Temporarily move root __init__.py to avoid pytest treating the project root
# as a package (directory name contains hyphens, invalid Python package name).
if os.path.exists(init_path):
    os.rename(init_path, init_backup)

try:
    if len(sys.argv) > 1:
        # If user passes arguments, override default test target
        args = [sys.executable, "-m", "pytest"] + sys.argv[1:] + ["-v"]
    else:
        # Default: run every test in tests/
        args = [sys.executable, "-m", "pytest", "tests", "-v"]
    result = subprocess.run(args, cwd=root)
    sys.exit(result.returncode)
finally:
    if os.path.exists(init_backup):
        os.rename(init_backup, init_path)
