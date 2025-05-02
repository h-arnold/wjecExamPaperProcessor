#!/usr/bin/env python3
"""
Test script for metadata extraction on a single file.
This script can be run with the VS Code debugger to test the metadata extraction process.
"""

import os
import sys
import json
from dotenv import load_dotenv

# Add project root directory to path to ensure imports work
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Load environment variables from root .env file
load_dotenv(os.path.join(project_root, '.env'))

# Import necessary modules from the project
from src.MetadataExtraction.main import extract_metadata_from_file

def test_metadata_extraction(
    ocr_file_path: str,
    api_key: str = None,
    provider: str = "mistral"
):
    """
    Test metadata extraction on a single file with configurable parameters.
    
    Args:
        ocr_file_path: Path to OCR JSON file to process
        api_key: API key for the LLM provider (will use env var if None)
        provider: LLM provider to use
        
    Returns:
        The extraction result dictionary
    """
    # If api_key is not provided, try to get it from environment variable
    if api_key is None:
        if provider == "mistral":
            api_key = os.environ.get("MISTRAL_API_KEY")
        
        if api_key is None:
            raise ValueError(f"API key not provided and {provider.upper()}_API_KEY not set in environment")
    
    # Check if MongoDB environment variables are set
    mongodb_uri = os.environ.get("MONGODB_URI")
    if not mongodb_uri:
        raise ValueError("MONGODB_URI not set in environment. MongoDB connection is required.")
    
    print(f"\n=== Testing metadata extraction on: {ocr_file_path} ===")
    print(f"Using provider: {provider}")
    print(f"MongoDB URI: {mongodb_uri.split('@')[0]}@...")  # Hide sensitive connection details
    
    # Call the extraction function
    result = extract_metadata_from_file(
        ocr_file_path=ocr_file_path,
        api_key=api_key,
        provider=provider
    )
    
    # Display detailed results for debugging
    print("\n=== Extracted Metadata ===")
    print(json.dumps(result["metadata"], indent=2))
    
    print("\n=== Processing Information ===")
    print(f"Document ID: {result['document_id']}")
    print(f"MongoDB ID: {result.get('mongodb_id', 'Not stored')}")
    
    if result.get("related_documents"):
        print("\n=== Related Documents ===")
        for doc in result["related_documents"]:
            print(f"- {doc['id']} ({doc['type']})")
    
    return result


if __name__ == "__main__":
    # Modify these values as needed for your testing
    
    # Sample OCR file to test with - replace with an actual file from your ocr_results folder
    TEST_OCR_FILE = "ocr_results/s23-1500u30-1.json"
    
    # API key - leave as None to use environment variable
    API_KEY = None
    
    # LLM provider to use
    PROVIDER = "mistral"
    
    # Run the test
    test_result = test_metadata_extraction(
        ocr_file_path=TEST_OCR_FILE,
        api_key=API_KEY,
        provider=PROVIDER
    )
    
    # Execution will stop here if you've set a breakpoint in the VS Code debugger
    print("\nTest completed successfully!")