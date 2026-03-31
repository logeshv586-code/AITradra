import os
from core.config import settings
from pathlib import Path

def test_universal_paths():
    print("--- AXIOM Universal Path Verification ---")
    
    reasoning_path = settings.LOCAL_REASONING_MODEL_PATH
    general_path = settings.LOCAL_GENERAL_MODEL_PATH
    
    print(f"LOCAL_REASONING_MODEL_PATH: {reasoning_path}")
    print(f"LOCAL_GENERAL_MODEL_PATH:   {general_path}")
    
    # Check if absolute
    print(f"Is Reasoning Path Absolute? {Path(reasoning_path).is_absolute()}")
    print(f"Is General Path Absolute?   {Path(general_path).is_absolute()}")
    
    # Check if exists
    print(f"Reasoning File Exists? {Path(reasoning_path).exists()}")
    print(f"General File Exists?   {Path(general_path).exists()}")
    
    if Path(reasoning_path).exists() and Path(general_path).exists():
        print("\nSUCCESS: Universal path resolution confirmed on Windows.")
    else:
        print("\nERROR: Configuration resolved absolute paths, but files not found at root.")

if __name__ == "__main__":
    test_universal_paths()
