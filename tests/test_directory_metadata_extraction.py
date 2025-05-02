#!/usr/bin/env python3
"""
Test script for metadata extraction on a directory of files.
This script can be run with the VS Code debugger to test the directory metadata extraction process.
"""

import os
import sys

# Add project root directory to path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import necessary modules from the project
from src.MetadataExtraction.main import extract_metadata_from_directory

def test_directory_metadata_extraction(
    ocr_directory_path: str,
    api_key: str = None,
    pattern: str = "*.json",
    provider: str = "mistral",
    batch_size: int = 20
):
    """
    Test metadata extraction on a directory of files with configurable parameters.
    
    Args:
        ocr_directory_path: Path to directory containing OCR JSON files
        api_key: API key for the LLM provider (will use env var if None)
        pattern: Glob pattern for matching OCR files
        provider: LLM provider to use
        batch_size: Number of documents to process in each batch
        
    Returns:
        List of extraction result dictionaries
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
    
    print(f"\n=== Testing directory metadata extraction on: {ocr_directory_path} ===")
    print(f"Using pattern: {pattern}")
    print(f"Using provider: {provider}")
    print(f"Batch size: {batch_size}")
    print(f"MongoDB URI: {mongodb_uri.split('@')[0]}@...")  # Hide sensitive connection details
    
    # Call the extraction function
    results = extract_metadata_from_directory(
        directory_path=ocr_directory_path,
        api_key=api_key,
        pattern=pattern,
        provider=provider,
        batch_size=batch_size
    )
    
    # Display summary of results
    print(f"\n=== Processed {len(results)} documents ===")
    
    # Group documents by type
    types = {}
    for result in results:
        doc_type = result['metadata'].get('paper_type', result['metadata'].get('Type', 'Unknown'))
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
            print(f"Type: {result['metadata'].get('paper_type', result['metadata'].get('Type', 'Unknown'))}")
            print(f"Year: {result['metadata'].get('year', result['metadata'].get('Year', 'N/A'))}")
            print(f"Qualification: {result['metadata'].get('qualification', result['metadata'].get('Qualification', 'N/A'))}")
            print(f"Subject: {result['metadata'].get('subject', result['metadata'].get('Subject', 'N/A'))}")
            print(f"MongoDB ID: {result.get('mongodb_id', 'Not stored')}")
    
    return results


if __name__ == "__main__":
    # Modify these values as needed for your testing
    
    # Directory containing OCR files to test with
    TEST_OCR_DIR = "ocr_results"
    
    # Pattern to match specific files (use "*.json" for all JSON files)
    TEST_PATTERN = "*.json"
    
    # API key - leave as None to use environment variable
    API_KEY = None
    
    # LLM provider to use
    PROVIDER = "mistral"
    
    # Batch size for processing multiple documents
    BATCH_SIZE = 20
    
    # Run the test
    test_results = test_directory_metadata_extraction(
        ocr_directory_path=TEST_OCR_DIR,
        api_key=API_KEY,
        pattern=TEST_PATTERN,
        provider=PROVIDER,
        batch_size=BATCH_SIZE
    )
    
    # Execution will stop here if you've set a breakpoint in the VS Code debugger
    print("\nTest completed successfully!")