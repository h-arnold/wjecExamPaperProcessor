import logging
from pathlib import Path
from .mistral_OCR_Client import MistralOCRClient
from src.FileManager.file_manager import FileManager
from src.DBManager.db_manager import DBManager
from src.Models.document import Document

class PDF_OCR_Processor:
    """
    Processes PDF files from a source directory using the MistralOCRClient.
    Stores all results in MongoDB using a hybrid storage approach.
    """
    def __init__(self, source_folder: str, ocr_client: MistralOCRClient, 
                db_manager: DBManager = None):
        """
        Initialise the PDF processor.

        Args:
            source_folder (str): Directory containing PDF files.
            ocr_client (MistralOCRClient): An instance of the OCR client.
            db_manager (DBManager): Optional DBManager instance. If not provided,
                                    a new instance will be created.
        """
        self.source_folder = Path(source_folder)
        self.ocr_client = ocr_client
        
        # Set up DBManager and FileManager
        self.db_manager = db_manager if db_manager is not None else DBManager()
        self.file_manager = FileManager()
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _delete_source_file(self, file_path):
        """
        Deletes a file from the filesystem.
        
        Args:
            file_path (Path): Path to the file to be deleted.
        """
        try:
            file_path.unlink()
            self.logger.info(f"Deleted source file: {file_path}")
        except Exception as e:
            self.logger.error(f"Error deleting file {file_path}: {e}")

    def process_pdfs(self):
        """
        Iterate through PDF files in the source folder, upload them, process them via OCR,
        and save the results in MongoDB.
        """
        pdf_files = list(self.source_folder.glob("*.pdf"))
        if not pdf_files:
            self.logger.info("No PDF files found in the source folder.")
            return
        
        processed_documents = []
        for pdf_file in pdf_files:
            try:
                self.logger.info(f"Processing file: {pdf_file.name}")
                
                # Create or retrieve Document object - document type is determined internally
                document = Document.from_pdf(pdf_file, self.db_manager)
                
                # Perform OCR processing
                if document and not document.processed:
                    success = document.perform_ocr(self.ocr_client)
                    if success:
                        processed_documents.append(document.document_id)
                        self.logger.info(f"Document processed with OCR and stored in MongoDB with ID: {document.document_id}")
                elif document:
                    processed_documents.append(document.document_id)
                    self.logger.info(f"Document already processed with ID: {document.document_id}")
                
                # Delete the source PDF file after successful processing
                self._delete_source_file(pdf_file)
                
            except Exception as e:
                self.logger.error(f"Error processing {pdf_file.name}: {e}")
        
        return processed_documents