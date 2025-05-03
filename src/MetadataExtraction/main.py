"""
Metadata extraction script for WJEC Exam Paper Processor.

This module provides functionality to extract metadata from OCR results
and store it in MongoDB.
"""

import os
import argparse
from pathlib import Path
from typing import Dict, Any, List, Union

from src.Llm_client.factory import LLMClientFactory
from src.MetadataExtraction.document_processor import DocumentProcessor
from src.FileManager.file_manager import FileManager
from src.DBManager.db_manager import DBManager


def extract_metadata_from_file(
    ocr_file_path: Union[str, Path],
    api_key: str,
    provider: str = "mistral"
) -> Dict[str, Any]:
    """
    Extract metadata from a single OCR JSON file and store in MongoDB.
    
    Args:
        ocr_file_path: Path to the OCR JSON file
        api_key: API key for the LLM provider
        provider: LLM provider to use
        
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
    
    # Create file manager for reading OCR files
    file_manager = FileManager()
    
    # Get MongoDB connection string from environment variable
    mongo_uri = os.environ.get("MONGODB_URI")
    if not mongo_uri:
        raise ValueError("MONGODB_URI environment variable must be set for MongoDB connection")
    
    # Create DB manager with the MongoDB connection
    db_manager = DBManager(connection_string=mongo_uri)
    
    # Create document processor with MongoDB connection
    processor = DocumentProcessor(
        llm_client=llm_client,
        file_manager=file_manager,
        db_manager=db_manager
    )
    
    # Process the document
    result = processor.process_document(ocr_file_path)
    
    print(f"\nSuccessfully processed document: {ocr_file_path}")
    print(f"Document ID: {result['document_id']}")
    print(f"Document Type: {result['metadata']['Type']}")
    
    return result


def extract_metadata_from_directory(
    directory_path: Union[str, Path],
    api_key: str,
    pattern: str = "*.json",
    provider: str = "mistral",
    batch_size: int = 20
) -> List[Dict[str, Any]]:
    """
    Extract metadata from all JSON files in a directory and store in MongoDB.
    
    Args:
        directory_path: Path to directory containing OCR JSON files
        api_key: API key for the LLM provider
        pattern: Glob pattern for matching OCR files
        provider: LLM provider to use
        batch_size: Size of batches for bulk operations
        
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
    
    # Create file manager for reading OCR files
    file_manager = FileManager()
    
    # Get MongoDB connection string from environment variable
    mongo_uri = os.environ.get("MONGODB_URI")
    if not mongo_uri:
        raise ValueError("MONGODB_URI environment variable must be set for MongoDB connection")
    
    # Create DB manager with the MongoDB connection
    db_manager = DBManager(connection_string=mongo_uri)
    
    # Create document processor with MongoDB connection
    processor = DocumentProcessor(
        llm_client=llm_client,
        file_manager=file_manager,
        db_manager=db_manager
    )
    
    # Process the directory
    results = processor.process_directory(directory_path, pattern, batch_size=batch_size)
    
    # Print summary
    print(f"\nProcessed {len(results)} documents from {directory_path}")
    print(f"Documents by type:")
    
    types = {}
    for result in results:
        doc_type = result['metadata'].get('paper_type', 
                 result['metadata'].get('Type', 'Unknown')) if 'metadata' in result else 'Unknown'
        if doc_type in types:
            types[doc_type] += 1
        else:
            types[doc_type] = 1
    
    for doc_type, count in types.items():
        print(f"- {doc_type}: {count}")
    
    return results


def main():
    """
    Command-line entry point for metadata extraction.
    
    This function provides a CLI interface for extracting metadata from WJEC exam paper OCR results
    and storing it in MongoDB.
    
    Arguments:
        No direct arguments, but accepts command-line arguments:
        --file, -f: Path to a single OCR JSON file to process
        --directory, -d: Path to directory containing OCR JSON files
        --pattern, -p: Glob pattern for matching OCR files (default: *.json)
        --provider: LLM provider to use (default: mistral)
        --api-key, -k: LLM API key (can also be set via environment variable)
        --db-connection: MongoDB connection string (can also be set via MONGODB_URI environment variable)
        --batch-size: Size of batches for bulk operations (default: 20)
    
    Returns:
        int: 0 for success, 1 for error conditions
    
    Examples:
        # Process a single file
        python metadata_extraction.py --file path/to/ocr_result.json
        
        # Process all JSON files in a directory
        python metadata_extraction.py --directory path/to/ocr_results
        
        # Process only specific JSON files
        python metadata_extraction.py --directory path/to/ocr_results --pattern "*_ocr.json"
        
        # Use a specific API key
        python metadata_extraction.py --file path/to/ocr_result.json --api-key YOUR_API_KEY
        
        # Use an environment variable for the API key
        # export MISTRAL_API_KEY=your_key
        python metadata_extraction.py --file path/to/ocr_result.json
    """
    parser = argparse.ArgumentParser(
        description='Extract metadata from WJEC exam paper OCR results and store in MongoDB.'
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
        '--provider',
        default='mistral',
        choices=['mistral'],  # Can add more providers later
        help='LLM provider to use (default: mistral)'
    )
    parser.add_argument(
        '--api-key', '-k',
        help='LLM API key (can also be set via environment variable)'
    )
    parser.add_argument(
        '--db-connection',
        help='MongoDB connection string (can also be set via MONGODB_URI environment variable)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=20,
        help='Size of batches for bulk operations (default: 20)'
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
    
    # Set up database connection
    db_connection = args.db_connection or os.environ.get('MONGODB_URI')
    if not db_connection:
        print("Note: No MongoDB connection string provided.")
        print("Using default connection. Set --db-connection or MONGODB_URI environment variable for custom connection.")
    
    # Configure MongoDB via environment variable for the DBManager to use
    if db_connection:
        os.environ['MONGODB_URI'] = db_connection
    
    # Process file or directory
    try:
        if args.file:
            extract_metadata_from_file(
                ocr_file_path=args.file,
                api_key=api_key,
                provider=args.provider
            )
        elif args.directory:
            extract_metadata_from_directory(
                directory_path=args.directory,
                api_key=api_key,
                pattern=args.pattern,
                provider=args.provider,
                batch_size=args.batch_size
            )
        else:
            print("Error: Either --file or --directory must be specified.")
            parser.print_help()
            return 1
            
    except ValueError as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())