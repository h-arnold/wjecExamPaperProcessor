import logging
from pathlib import Path
from .mistral_OCR_Client import MistralOCRClient
from src.FileManager.file_manager import FileManager
from src.DBManager.db_manager import DBManager

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
        self.file_manager = FileManager(self.db_manager)
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _serialise_ocr_result(self, obj):
        """
        Convert OCR result objects to serialisable dictionaries.
        """
        if hasattr(obj, '__dict__'):
            # For custom objects with __dict__ attribute
            result = {}
            for key, value in obj.__dict__.items():
                # Skip private attributes
                if not key.startswith('_'):
                    if isinstance(value, list):
                        result[key] = [self._serialise_ocr_result(item) for item in value]
                    else:
                        result[key] = self._serialise_ocr_result(value)
            return result
        elif isinstance(obj, list):
            return [self._serialise_ocr_result(item) for item in obj]
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            # For other types, convert to string
            return str(obj)

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

    def _determine_document_type(self, pdf_file):
        """
        Determine the document type (Question Paper or Mark Scheme) based on filename.
        
        Args:
            pdf_file (Path or str): Path to the PDF file
            
        Returns:
            str: Document type ("Question Paper" or "Mark Scheme")
        """
        pdf_path = Path(pdf_file)
        filename = pdf_path.name.lower()
        
        if "ms" in filename or "mark scheme" in filename or "markscheme" in filename:
            return "Mark Scheme"
        else:
            return "Question Paper"

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
                
                # Process the PDF and store in MongoDB
                document_id = self.process_pdf(pdf_file)
                if document_id:
                    processed_documents.append(document_id)
                    self.logger.info(f"Document stored in MongoDB with ID: {document_id}")
                
                # Delete the source PDF file after successful processing
                self._delete_source_file(pdf_file)
                
            except Exception as e:
                self.logger.error(f"Error processing {pdf_file.name}: {e}")
        
        return processed_documents

    def process_pdf(self, pdf_file):
        """
        Process a PDF file and store it in MongoDB using the hybrid approach.
        
        Args:
            pdf_file (Path): Path to the PDF file to process
            
        Returns:
            str: Document ID if successful, None otherwise
        """
        try:
            self.logger.info(f"Uploading file: {pdf_file.name}")
            # Step 1: Upload the PDF file and get the file_id
            uploaded_file = self.ocr_client.upload_pdf(str(pdf_file))
            file_id = uploaded_file.id
            self.logger.info(f"File uploaded successfully. File ID: {file_id}")
            
            # Step 2: Get the signed URL using the file_id
            signed_url_response = self.ocr_client.get_signed_url(file_id)
            signed_url = signed_url_response.url
            self.logger.info(f"Retrieved signed URL for processing")
            
            # Step 3: Process OCR with the signed URL
            self.logger.info(f"Processing OCR for file: {pdf_file.name}")
            ocr_result = self.ocr_client.ocr_pdf(signed_url)
            
            # Step 4: Serialize the OCR result pages before storing in MongoDB
            # Use the existing serialization method
            serialized_pages = [self._serialise_ocr_result(page) for page in ocr_result.pages]
            
            # Step 5: Store PDF, OCR results, and images in MongoDB
            document_type = self._determine_document_type(pdf_file)
            document_id = self.file_manager.add_document_to_db_with_images(
                pdf_file, 
                serialized_pages, 
                document_type
            )
            
            return document_id
            
        except Exception as e:
            self.logger.error(f"Error processing {pdf_file.name} for MongoDB: {e}")
            raise
