"""Pytest configuration and root path resolution."""

import sys
from pathlib import Path

# Programmatically ensure the project root directory is always on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
