import subprocess
import sys
import os

if os.name == "nt":
    pip_path = "pip"
else:
    pip_path = "pip3"

# Install requirements.txt
if os.path.exists("requirements.txt"):
    subprocess.check_call([pip_path, "install", "-r", "requirements.txt"])
    print("Packages from requirements.txt have been installed.")
else:
    print("requirements.txt file not found.")