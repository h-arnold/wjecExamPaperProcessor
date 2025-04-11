#!/usr/bin/env python3
"""
Test script for metadata extraction on a directory of files.
This script can be run with the VS Code debugger to test the directory metadata extraction process.
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import necessary modules from the project
from MetadataExtraction.main import extract_metadata_from_directory

def test_directory_metadata_extraction(
    ocr_directory_path: str,
    api_key: str = None,
    prompt_path: str = "Prompts/metadataCreator.md",
    pattern: str = "*.json",
    base_metadata_dir: str = "test_metadata",
    index_path: str = "test_index.json",
    provider: str = "mistral"
):
    """
    Test metadata extraction on a directory of files with configurable parameters.
    
    Args:
        ocr_directory_path: Path to directory containing OCR JSON files
        api_key: API key for the LLM provider (will use env var if None)
        prompt_path: Path to metadata extraction prompt
        pattern: Glob pattern for matching OCR files
        base_metadata_dir: Base directory for metadata files
        index_path: Path to the index file
        provider: LLM provider to use
        
    Returns:
        List of extraction result dictionaries
    """
    # If api_key is not provided, try to get it from environment variable
    if api_key is None:
        if provider == "mistral":
            api_key = os.environ.get("MISTRAL_API_KEY")
        
        if api_key is None:
            raise ValueError(f"API key not provided and {provider.upper()}_API_KEY not set in environment")
    
    print(f"\n=== Testing directory metadata extraction on: {ocr_directory_path} ===")
    print(f"Using pattern: {pattern}")
    print(f"Using prompt: {prompt_path}")
    print(f"Using provider: {provider}")
    print(f"Metadata will be saved to: {base_metadata_dir}")
    print(f"Index will be saved to: {index_path}")
    
    # Call the extraction function
    results = extract_metadata_from_directory(
        directory_path=ocr_directory_path,
        api_key=api_key,
        pattern=pattern,
        base_metadata_dir=base_metadata_dir,
        index_path=index_path,
        provider=provider
    )
    
    # Display summary of results
    print(f"\n=== Processed {len(results)} documents ===")
    
    # Group documents by type
    types = {}
    for result in results:
        doc_type = result['metadata'].get('Type')
        if doc_type in types:
            types[doc_type] += 1
        else:
            types[doc_type] = 1
    
    print("\n=== Document Types ===")
    for doc_type, count in types.items():
        print(f"- {doc_type}: {count}")
    
    # Print details of first few documents
    max_details = min(3, len(results))
    if max_details > 0:
        print(f"\n=== Sample Details (first {max_details} documents) ===")
        for i in range(max_details):
            result = results[i]
            print(f"\nDocument {i+1}:")
            print(f"ID: {result['document_id']}")
            print(f"Type: {result['metadata']['Type']}")
            print(f"Year: {result['metadata'].get('Year', 'N/A')}")
            print(f"Qualification: {result['metadata'].get('Qualification', 'N/A')}")
            print(f"Subject: {result['metadata'].get('Subject', 'N/A')}")
            print(f"Metadata saved to: {result['metadata_path']}")
    
    return results


if __name__ == "__main__":
    # Modify these values as needed for your testing
    
    # Directory containing OCR files to test with
    TEST_OCR_DIR = "ocr_results"
    
    # Pattern to match specific files (use "*.json" for all JSON files)
    TEST_PATTERN = "*.json"
    
    # API key - leave as None to use environment variable
    API_KEY = None
    
    # Where to save test metadata (different from production to avoid mixing)
    TEST_METADATA_DIR = "Index/metadata"
    
    # Where to save test index (different from production to avoid mixing)
    TEST_INDEX_PATH = "Index/index.json"
    
    # LLM provider to use
    PROVIDER = "mistral"
    
    
    # Run the test
    test_results = test_directory_metadata_extraction(
        ocr_directory_path=TEST_OCR_DIR,
        api_key=API_KEY,
        pattern=TEST_PATTERN,
        base_metadata_dir=TEST_METADATA_DIR,
        index_path=TEST_INDEX_PATH,
        provider=PROVIDER
    )
    
    # Execution will stop here if you've set a breakpoint in the VS Code debugger
    print("\nTest completed successfully!")