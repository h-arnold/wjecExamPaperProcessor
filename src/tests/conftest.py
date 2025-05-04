"""
Pytest configuration file for providing fixtures used across multiple test files.
"""

import os
import sys
import pytest
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def ocr_directory_path() -> str:
    """
    Fixture that returns the path to the OCR results directory from the .env file.
    
    Returns:
        str: Path to the OCR results directory
    """
    # Get the OCR directory from .env or use the default
    ocr_dir = os.environ.get('DESTINATION_FOLDER', 'ocr_results')
    
    # Make sure the path is absolute
    if not os.path.isabs(ocr_dir):
        # Get the project root directory (parent of tests folder)
        project_root = Path(__file__).parent.parent
        ocr_dir = os.path.join(project_root, ocr_dir)
    
    print(f"Using OCR directory: {ocr_dir}")
    return ocr_dir

@pytest.fixture
def ocr_file_path(ocr_directory_path) -> str:
    """
    Fixture that returns a sample OCR file path for testing.
    
    Args:
        ocr_directory_path: The path to the OCR directory
        
    Returns:
        str: Path to a sample OCR file
    """
    # Use a sample file that we know exists in the OCR directory
    sample_file = "s23-1500u30-1.json"
    file_path = os.path.join(ocr_directory_path, sample_file)
    
    # Check if the file exists, if not try to find an alternative
    if not os.path.exists(file_path):
        # Look for any .json file in the OCR directory
        for file in os.listdir(ocr_directory_path):
            if file.endswith('.json') and os.path.isfile(os.path.join(ocr_directory_path, file)):
                file_path = os.path.join(ocr_directory_path, file)
                break
    
    print(f"Using OCR file: {file_path}")
    return file_path