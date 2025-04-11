"""
Configuration file for pytest that automatically adjusts the Python path.

This file is automatically loaded by pytest before running tests.
It adds the project root directory to sys.path so that imports like 'src.ModuleName' work correctly.
"""
import os
import sys

# Add the project root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))