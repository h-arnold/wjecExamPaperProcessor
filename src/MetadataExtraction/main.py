"""
Metadata extraction script for WJEC Exam Paper Processor.

This module provides functionality to extract metadata from OCR results
without interfering with the existing OCR process. It can be called
independently as part of a multi-stage processing pipeline.
"""

import os
import argparse
from pathlib import Path
from typing import Dict, Any, List, Union

from src.Llm_client.factory import LLMClientFactory
from src.MetadataExtraction.document_processor import DocumentProcessor
from src.FileManager.file_manager import MetadataFileManager
from src.IndexManager.index_manager import IndexManager



def extract_metadata_from_file(
    ocr_file_path: Union[str, Path],
    api_key: str,
    base_metadata_dir: str = "metadata",
    index_path: str = "index.json",
    provider: str = "mistral",
    use_db: bool = True
) -> Dict[str, Any]:
    """
    Extract metadata from a single OCR JSON file.
    
    Args:
        ocr_file_path: Path to the OCR JSON file
        api_key: API key for the LLM provider
        base_metadata_dir: Base directory for metadata files
        index_path: Path to the index file
        provider: LLM provider to use
        use_db: Whether to use database functionality (default True)
        
    Returns:
        Dict containing the extracted metadata and processing information
    """
    # Create LLM client using the factory instance
    factory = LLMClientFactory()
    llm_client = factory.create_specific_client(
        provider=provider,
        api_key=api_key,
        model="mistral-small-latest" if provider == "mistral" else None
    )
    
   
    # Create file and index managers first
    file_manager = MetadataFileManager(base_dir=base_metadata_dir)
    index_manager = IndexManager(index_path=index_path)
    
    # Create document processor with properly instantiated managers
    processor = DocumentProcessor(
        llm_client=llm_client,
        file_manager=file_manager,
        index_manager=index_manager,
        use_db=use_db
    )
    
   
    # Process the document
    store_in_db = use_db  # Only try to store in DB if use_db is True
    result = processor.process_document(ocr_file_path, store_in_db=store_in_db, store_in_file=True)
    
    print(f"\nSuccessfully processed document: {ocr_file_path}")
    print(f"Document ID: {result['document_id']}")
    print(f"Document Type: {result['metadata']['Type']}")
    print(f"Metadata saved to: {result['metadata_path']}")
    
    # Print related documents if any
    if result['related_documents']:
        print("\nRelated documents:")
        for doc in result['related_documents']:
            print(f"- {doc['id']} ({doc['type']})")
    else:
        print("\nNo related documents found.")
    
    return result


def extract_metadata_from_directory(
    directory_path: Union[str, Path],
    api_key: str,
    pattern: str = "*.json",
    base_metadata_dir: str = "metadata",
    index_path: str = "index.json",
    provider: str = "mistral"
) -> List[Dict[str, Any]]:
    """
    Extract metadata from all JSON files in a directory.
    
    Args:
        directory_path: Path to directory containing OCR JSON files
        api_key: API key for the LLM provider
        pattern: Glob pattern for matching OCR files
        base_metadata_dir: Base directory for metadata files
        index_path: Path to the index file
        provider: LLM provider to use
        
    Returns:
        List of dictionaries containing extraction results
    """
    # Create LLM client using the factory instance
    factory = LLMClientFactory()
    llm_client = factory.create_specific_client(
        provider=provider,
        api_key=api_key,
        model="mistral-small-latest" if provider == "mistral" else None
    )
    
    
    # Create file and index managers first
    file_manager = MetadataFileManager(base_dir=base_metadata_dir)
    index_manager = IndexManager(index_path=index_path)
    
    # Create document processor with properly instantiated managers
    processor = DocumentProcessor(
        llm_client=llm_client,
        file_manager=file_manager,
        index_manager=index_manager
    )
    

    # Process the directory
    results = processor.process_directory(directory_path, pattern)
    
    # Print summary
    print(f"\nProcessed {len(results)} documents from {directory_path}")
    print(f"Documents by type:")
    
    types = {}
    for result in results:
        doc_type = result['metadata'].get('Type')
        if doc_type in types:
            types[doc_type] += 1
        else:
            types[doc_type] = 1
    
    for doc_type, count in types.items():
        print(f"- {doc_type}: {count}")
    
    return results


def main():
    """Command-line entry point for metadata extraction.
    This function provides a CLI interface for extracting metadata from WJEC exam paper OCR results.
    It handles processing either a single file or multiple files in a directory,
    and manages the LLM API keys and other configuration options.
    Arguments:
        No direct arguments, but accepts command-line arguments:
        --file, -f: Path to a single OCR JSON file to process
        --directory, -d: Path to directory containing OCR JSON files
        --pattern, -p: Glob pattern for matching OCR files (default: *.json)
        --metadata-dir: Base directory for metadata files (default: metadata)
        --index: Path to the index file (default: index.json)
        --provider: LLM provider to use (default: mistral)
        --api-key, -k: LLM API key (can also be set via environment variable)
    Returns:
        int: 0 for success, 1 for error conditions
    Examples:
        # Process a single file
        python metadata_extraction.py --file path/to/ocr_result.json
        # Process all JSON files in a directory
        python metadata_extraction.py --directory path/to/ocr_results
        # Process only specific JSON files
        python metadata_extraction.py --directory path/to/ocr_results --pattern "*_ocr.json"
        # Specify a custom prompt
        python metadata_extraction.py --file path/to/ocr_result.json --prompt custom_prompt.md
        # Use a specific API key
        python metadata_extraction.py --file path/to/ocr_result.json --api-key YOUR_API_KEY
        # Use an environment variable for the API key
        # export MISTRAL_API_KEY=your_key
        python metadata_extraction.py --file path/to/ocr_result.json
    """
    """Command-line entry point for metadata extraction."""
    parser = argparse.ArgumentParser(
        description='Extract metadata from WJEC exam paper OCR results.'
    )
    
    # Define command-line arguments
    parser.add_argument(
        '--file', '-f',
        help='Path to a single OCR JSON file to process'
    )
    parser.add_argument(
        '--directory', '-d',
        default="ocr_results",
        help='Path to directory containing OCR JSON files'
    )
    parser.add_argument(
        '--pattern', '-p',
        default='*.json',
        help='Glob pattern for matching OCR files (default: *.json)'
    )
    parser.add_argument(
        '--metadata-dir',
        default='metadata',
        help='Base directory for metadata files (default: metadata)'
    )
    parser.add_argument(
        '--index',
        default='index.json',
        help='Path to the index file (default: index.json)'
    )
    parser.add_argument(
        '--provider',
        default='mistral',
        choices=['mistral'],  # Can add more providers later
        help='LLM provider to use (default: mistral)'
    )
    parser.add_argument(
        '--api-key', '-k',
        help='LLM API key (can also be set via environment variable)'
    )
    
    args = parser.parse_args()
    
    # Get API key from args or environment
    api_key = args.api_key
    if not api_key:
        if args.provider == 'mistral':
            api_key = os.environ.get('MISTRAL_API_KEY')
        # Add more provider-specific environment variables here
    
    if not api_key:
        print(f"Error: API key not provided for {args.provider}.")
        print(f"Use --api-key or set {args.provider.upper()}_API_KEY environment variable.")
        return 1
    
    # Process file or directory
    if args.file:
        extract_metadata_from_file(
            ocr_file_path=args.file,
            api_key=api_key,
            base_metadata_dir=args.metadata_dir,
            index_path=args.index,
            provider=args.provider
        )
    elif args.directory:
        extract_metadata_from_directory(
            directory_path=args.directory,
            api_key=api_key,
            pattern=args.pattern,
            base_metadata_dir=args.metadata_dir,
            index_path=args.index,
            provider=args.provider
        )
    else:
        print("Error: Either --file or --directory must be specified.")
        parser.print_help()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())