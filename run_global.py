import subprocess
import os

if os.name == "nt":
    python_path = "python"
else:
    python_path = "python3"

# Chạy app.py bằng Python toàn cục
try:
    subprocess.check_call([python_path, "app.py"])
except subprocess.CalledProcessError as e:
    print(f"Error running app.py: {e}")