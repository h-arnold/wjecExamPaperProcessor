#!/usr/bin/env python3
"""
Command-line entry point for updating the index with unit numbers and relationships.
"""

import sys
from src.IndexManager.main import main

if __name__ == "__main__":
    sys.exit(main())