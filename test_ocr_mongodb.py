#!/usr/bin/env python3
"""
Test script for MongoDB hybrid storage functionality.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from src.OCR.mistral_OCR_Client import MistralOCRClient
from src.OCR.pdf_Ocr_Processor import PDF_OCR_Processor
from src.DBManager.db_manager import DBManager

def test_mongodb_storage():
    """
    Test the MongoDB hybrid storage approach with PDFs in the source folder.
    """
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("test_mongodb_storage")
    
    # Load environment variables
    load_dotenv()
    
    # Get environment variables
    source_folder = os.environ.get("SOURCE_FOLDER")
    destination_folder = os.environ.get("DESTINATION_FOLDER")
    mistral_api_key = os.environ.get("MISTRAL_API_KEY")
    mongodb_uri = os.environ.get("MONGODB_URI")
    mongodb_db = os.environ.get("MONGODB_DATABASE_NAME")
    
    # Validate environment variables
    if not all([source_folder, destination_folder, mistral_api_key, mongodb_uri, mongodb_db]):
        logger.error("Missing required environment variables")
        return
    
    logger.info(f"Using source folder: {source_folder}")
    logger.info(f"Using MongoDB database: {mongodb_db}")
    
    # Initialize database manager
    db_manager = DBManager(connection_string=mongodb_uri, database_name=mongodb_db)
    
    # Initialize OCR client
    ocr_client = MistralOCRClient(api_key=mistral_api_key)
    
    # Initialize PDF processor with MongoDB storage
    processor = PDF_OCR_Processor(
        source_folder,
        destination_folder,
        ocr_client,
        use_mongodb=True,
        db_manager=db_manager
    )
    
    # Process PDFs
    logger.info("Starting PDF processing with MongoDB storage")
    processed_docs = processor.process_pdfs()
    
    # Print results
    if processed_docs:
        logger.info(f"Successfully processed {len(processed_docs)} documents")
        for doc_id in processed_docs:
            logger.info(f"Document ID: {doc_id}")
    else:
        logger.info("No documents were processed")

if __name__ == "__main__":
    test_mongodb_storage()
