#!/usr/bin/env python3
"""
Test script for metadata extraction on a single file.
This script can be run with the VS Code debugger to test the metadata extraction process.
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import necessary modules from the project
from src.metadata_extraction import extract_metadata_from_file
from src.llm_client.factory import LLMClientFactory
from src.document_processor import DocumentProcessor


def test_metadata_extraction(
    ocr_file_path: str,
    api_key: str = None,
    prompt_path: str = "Prompts/metadataCreator.md",
    base_metadata_dir: str = "test_metadata",
    index_path: str = "test_index.json",
    provider: str = "mistral"
):
    """
    Test metadata extraction on a single file with configurable parameters.
    
    Args:
        ocr_file_path: Path to OCR JSON file to process
        api_key: API key for the LLM provider (will use env var if None)
        prompt_path: Path to metadata extraction prompt
        base_metadata_dir: Base directory for metadata files
        index_path: Path to the index file
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
    
    print(f"\n=== Testing metadata extraction on: {ocr_file_path} ===")
    print(f"Using prompt: {prompt_path}")
    print(f"Using provider: {provider}")
    print(f"Metadata will be saved to: {base_metadata_dir}")
    print(f"Index will be saved to: {index_path}")
    
    # Call the extraction function
    result = extract_metadata_from_file(
        ocr_file_path=ocr_file_path,
        api_key=api_key,
        prompt_path=prompt_path,
        base_metadata_dir=base_metadata_dir,
        index_path=index_path,
        provider=provider
    )
    
    # Display detailed results for debugging
    print("\n=== Extracted Metadata ===")
    print(json.dumps(result["metadata"], indent=2))
    
    print("\n=== Processing Information ===")
    print(f"Document ID: {result['document_id']}")
    print(f"Metadata saved to: {result['metadata_path']}")
    
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
    
    # Where to save test metadata (different from production to avoid mixing)
    TEST_METADATA_DIR = "test_metadata"
    
    # Where to save test index (different from production to avoid mixing)
    TEST_INDEX_PATH = "test_index.json"
    
    # LLM provider to use
    PROVIDER = "mistral"
    
    # Path to prompt file
    PROMPT_PATH = "Prompts/metadataCreator.md"
    
    # Run the test
    test_result = test_metadata_extraction(
        ocr_file_path=TEST_OCR_FILE,
        api_key=API_KEY,
        prompt_path=PROMPT_PATH,
        base_metadata_dir=TEST_METADATA_DIR,
        index_path=TEST_INDEX_PATH,
        provider=PROVIDER
    )
    
    # Execution will stop here if you've set a breakpoint in the VS Code debugger
    print("\nTest completed successfully!")