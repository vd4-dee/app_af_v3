import subprocess
import sys
import os

venv_dir = "venv"

# Create virtual environment
if not os.path.exists(venv_dir):
    subprocess.check_call([sys.executable, "-m", "venv", venv_dir])
    print(f"Virtual environment created at: {venv_dir}")
else:
    print(f"Virtual environment already exists at: {venv_dir}")

# Determine pip path in the virtual environment
if os.name == "nt":
    pip_path = os.path.join(venv_dir, "Scripts", "pip.exe")
else:
    pip_path = os.path.join(venv_dir, "bin", "pip")

# Install requirements.txt
if os.path.exists("requirements.txt"):
    subprocess.check_call([pip_path, "install", "-r", "requirements.txt"])
    print("Packages from requirements.txt have been installed.")
else:
    print("requirements.txt file not found.")