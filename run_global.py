import subprocess
import os
import sys

# Add the project root to the Python path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

if os.name == "nt":
    python_path = "python"
else:
    python_path = "python3"

# Chạy app.py bằng Python toàn cục
try:
    subprocess.check_call([python_path, "app.py"])
except subprocess.CalledProcessError as e:
    print(f"Error running app.py: {e}")
    sys.exit(1)