import os
import json
import base64
import logging
from pathlib import Path
from .mistral_OCR_Client import MistralOCRClient
from src.FileManager.file_manager import FileManager
from src.DBManager.db_manager import DBManager

class PDF_OCR_Processor:
    """
    Processes PDF files from a source directory using the MistralOCRClient.
    Can store results in the filesystem or in MongoDB using a hybrid approach.
    """
    def __init__(self, source_folder: str, destination_folder: str, ocr_client: MistralOCRClient, 
                use_mongodb: bool = False, db_manager: DBManager = None):
        """
        Initialise the PDF processor.

        Args:
            source_folder (str): Directory containing PDF files.
            destination_folder (str): Directory where OCR results will be saved if not using MongoDB.
            ocr_client (MistralOCRClient): An instance of the OCR client.
            use_mongodb (bool): Whether to use MongoDB for storage instead of filesystem.
            db_manager (DBManager): Optional DBManager instance. If using MongoDB and not provided,
                                    a new instance will be created.
        """
        self.source_folder = Path(source_folder)
        self.destination_folder = Path(destination_folder)
        self.ocr_client = ocr_client
        self.use_mongodb = use_mongodb
        
        # Create destination folder if using filesystem storage
        if not self.use_mongodb:
            self.destination_folder.mkdir(parents=True, exist_ok=True)
        
        # Set up DBManager and FileManager if using MongoDB
        if self.use_mongodb:
            self.db_manager = db_manager if db_manager is not None else DBManager()
            self.file_manager = FileManager(self.db_manager)
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _extract_and_save_images(self, ocr_result, pdf_stem):
        """
        Extract base64 encoded images from OCR result and save them as binary files.
        Used only when not storing in MongoDB.
        
        Args:
            ocr_result: The OCR result containing pages with images
            pdf_stem: The stem name of the PDF file (without extension)
            
        Returns:
            Updated OCR result with image paths instead of base64 data
        """
        # Create image directory for this PDF
        image_dir = self.destination_folder / pdf_stem / "images"
        image_dir.mkdir(parents=True, exist_ok=True)
        
        # Process each page
        updated_result = []
        for page in ocr_result:
            updated_page = self._serialise_ocr_result(page)
            
            # Process images in page
            if 'images' in updated_page and updated_page['images']:
                for i, img in enumerate(updated_page['images']):
                    if 'image_base64' in img and img['image_base64']:
                        # Extract image data and format
                        img_data = img['image_base64']
                        if ',' in img_data:
                            # Handle format like "data:image/jpeg;base64,/9j/4AAQ..."
                            format_part, base64_data = img_data.split(',', 1)
                            img_format = format_part.split(';')[0].split('/')[1]
                        else:
                            # Assume JPEG if no format specified
                            base64_data = img_data
                            img_format = 'jpeg'
                        
                        # Create filename
                        img_filename = f"img_{page.index if hasattr(page, 'index') else i}_{i}.{img_format}"
                        img_path = image_dir / img_filename
                        
                        # Save image to file
                        try:
                            with open(img_path, 'wb') as f:
                                f.write(base64.b64decode(base64_data))
                            
                            # Update reference in the result
                            img['image_path'] = str(img_path.relative_to(self.destination_folder))
                            del img['image_base64']
                            
                            self.logger.info(f"Extracted image saved to {img_path}")
                        except Exception as e:
                            self.logger.error(f"Error saving image {img_filename}: {e}")
            
            updated_result.append(updated_page)
        
        return updated_result
    
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
        and save the results as JSON files in the destination folder or MongoDB.
        """
        pdf_files = list(self.source_folder.glob("*.pdf"))
        if not pdf_files:
            self.logger.info("No PDF files found in the source folder.")
            return
        
        processed_documents = []
        
        for pdf_file in pdf_files:
            try:
                self.logger.info(f"Processing file: {pdf_file.name}")
                
                if self.use_mongodb:
                    # Process using MongoDB hybrid storage
                    document_id = self.process_pdf_mongodb(pdf_file)
                    if document_id:
                        processed_documents.append(document_id)
                        self.logger.info(f"Document stored in MongoDB with ID: {document_id}")
                else:
                    # Process using filesystem storage
                    output_file = self.process_pdf_filesystem(pdf_file)
                    if output_file:
                        processed_documents.append(str(output_file))
                        self.logger.info(f"OCR result saved to {output_file}")
                
                # Delete the source PDF file after successful processing
                self._delete_source_file(pdf_file)
                
            except Exception as e:
                self.logger.error(f"Error processing {pdf_file.name}: {e}")
        
        return processed_documents

    def process_pdf_mongodb(self, pdf_file):
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
    
    def process_pdf_filesystem(self, pdf_file):
        """
        Process a PDF file and store it in the filesystem.
        
        Args:
            pdf_file (Path): Path to the PDF file to process
            
        Returns:
            Path: Path to the saved JSON file if successful, None otherwise
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
            
            # Extract and save images, then serialize the OCR result
            extracted_result = self._extract_and_save_images(ocr_result.pages, pdf_file.stem)
            
            # Save the serialized OCR result to the destination folder
            output_file = self.destination_folder / (pdf_file.stem + ".json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(extracted_result, f, indent=4)
            
            return output_file
            
        except Exception as e:
            self.logger.error(f"Error processing {pdf_file.name} for filesystem: {e}")
            raise
