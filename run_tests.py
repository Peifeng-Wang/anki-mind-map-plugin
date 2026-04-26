import os
import subprocess
import sys

root = os.path.dirname(os.path.abspath(__file__))

if len(sys.argv) > 1:
    args = [sys.executable, "-m", "pytest"] + sys.argv[1:] + ["-v"]
else:
    args = [sys.executable, "-m", "pytest", "tests", "-v"]

result = subprocess.run(args, cwd=root)
sys.exit(result.returncode)
