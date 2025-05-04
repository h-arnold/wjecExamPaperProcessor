import os
from pathlib import Path
from dotenv import load_dotenv
from .mistral_OCR_Client import MistralOCRClient
from .pdf_Ocr_Processor import PDF_OCR_Processor
from src.DBManager.db_manager import DBManager

def main() -> int:
    """
    Main entry point for OCR processing pipeline.
    Returns:
        int: 0 for success, 1 for failure
    """
    # Load environment variables from .env file in project root
    dotenv_path = Path(__file__).parents[2] / ".env"
    load_dotenv(dotenv_path=dotenv_path)
    
    # Retrieve the source folder from environment variables.
    source_folder = os.getenv("SOURCE_FOLDER")
    dest_folder = os.getenv("DESTINATION_FOLDER")
    api_key = os.getenv("MISTRAL_API_KEY")

    if not all([source_folder, dest_folder, api_key]):
        print("Error: Required environment variables not set")
        print(f"SOURCE_FOLDER: {'✓' if source_folder else '✗'}")
        print(f"DESTINATION_FOLDER: {'✓' if dest_folder else '✗'}")
        print(f"MISTRAL_API_KEY: {'✓' if api_key else '✗'}")
        return 1
    
    # MongoDB connection settings
    mongodb_uri = os.environ.get("MONGODB_URI")
    if not mongodb_uri:
        raise EnvironmentError("MONGODB_URI environment variable not set.")
    
    mongodb_db = os.environ.get("MONGODB_DATABASE_NAME", "wjec_exams")
    
    # Initialise the database manager
    db_manager = DBManager(connection_string=mongodb_uri, database_name=mongodb_db)
    
    # Ensure the database is initialised
    if not db_manager.initialise_database():
        raise EnvironmentError("Failed to initialise MongoDB database")
    
    # Initialise the Mistral OCR client using the MistralAI Python library.
    ocr_client = MistralOCRClient(api_key=api_key)
    
    # Initialise and run the PDF OCR processor.
    processor = PDF_OCR_Processor(
        source_folder, 
        ocr_client,
        db_manager=db_manager
    )
    
    # Process the PDFs and get the list of processed document IDs
    processed_documents = processor.process_pdfs()
    
    if processed_documents:
        print(f"Successfully processed {len(processed_documents)} documents.")
        for doc_id in processed_documents:
            print(f"Processed: {doc_id}")
    else:
        print("No documents were processed.")
    
    try:
        print("OCR processing completed successfully.")
        return 0
    except Exception as e:
        print(f"Error during OCR processing: {str(e)}")
        return 1

if __name__ == "__main__":
    main()
