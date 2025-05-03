import os
from pathlib import Path
from dotenv import load_dotenv
from .mistral_OCR_Client import MistralOCRClient
from .pdf_Ocr_Processor import PDF_OCR_Processor
from src.DBManager.db_manager import DBManager

def main():
    """
    Main function to run the PDF OCR processing.
    Uses MongoDB with hybrid storage approach by default.
    """
    # Load environment variables from .env file in project root
    dotenv_path = Path(__file__).parents[2] / ".env"
    load_dotenv(dotenv_path=dotenv_path)
    
    # Retrieve the source and destination folders from environment variables.
    source_folder = os.environ.get("SOURCE_FOLDER")
    if not source_folder:
        raise EnvironmentError("SOURCE_FOLDER environment variable not set.")
    
    destination_folder = os.environ.get("DESTINATION_FOLDER")
    if not destination_folder:
        raise EnvironmentError("DESTINATION_FOLDER environment variable not set.")
    
    # Retrieve the Mistral API key from the environment.
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise EnvironmentError("MISTRAL_API_KEY environment variable not set.")
    
    # Check if we should use filesystem storage instead of MongoDB
    use_filesystem = os.environ.get("USE_FILESYSTEM_STORAGE", "False").lower() == "true"
    
    # MongoDB connection settings if using MongoDB
    if not use_filesystem:
        mongodb_uri = os.environ.get("MONGODB_URI")
        mongodb_db = os.environ.get("MONGODB_DATABASE_NAME", "wjec_exams")
        
        # Initialise the database manager
        db_manager = DBManager(connection_string=mongodb_uri, database_name=mongodb_db)
        
        # Ensure the database is initialised
        if not db_manager.initialise_database():
            raise EnvironmentError("Failed to initialise MongoDB database")
    else:
        db_manager = None
    
    # Initialise the Mistral OCR client using the MistralAI Python library.
    ocr_client = MistralOCRClient(api_key=api_key)
    
    # Initialise and run the PDF OCR processor.
    processor = PDF_OCR_Processor(
        source_folder, 
        destination_folder, 
        ocr_client,
        use_mongodb=(not use_filesystem),
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

if __name__ == "__main__":
    main()
