import os
from pathlib import Path

# Directories to skip during traversal
SKIP_DIRS = {
    ".venv", ".env", "__pycache__", ".git", ".pytest_cache",
    ".research_cache", ".ruff_cache", "node_modules", ".eggs", "*.egg-info",
    "results", "archive", "tests", "src", "legacy"
}

def list_all_contents(root_dir: str):
    """
    Recursively list all files and folders under root_dir, excluding standard ignore patterns.
    Returns a list of paths relative to root_dir.
    """
    root = Path(root_dir)
    all_items = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out skip directories in-place to prevent os.walk from descending into them
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        
        rel_dir = Path(dirpath).relative_to(root)
        for dirname in dirnames:
            all_items.append(str(rel_dir / dirname))
        for filename in filenames:
            all_items.append(str(rel_dir / filename))
    return all_items

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python list_all_contents.py <folder>")
        sys.exit(1)
    folder = sys.argv[1]
    items = list_all_contents(folder)
    for item in items:
        print(item)
