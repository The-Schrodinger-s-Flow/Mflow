import subprocess
import sys

packages = [
    "numpy",
    "scikit-image",
    "matplotlib",
    "sangaboard",
    "scipy",
]

for package in packages:
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    except subprocess.CalledProcessError:
        print(f"Retrying {package} with --break-system-packages...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "--break-system-packages",
            package
        ])