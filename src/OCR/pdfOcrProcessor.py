import os
import json
import base64
import logging
from pathlib import Path
from .mistralOCRClient import MistralOCRClient

class PDF_OCR_Processor:
    """
    Processes PDF files from a source directory using the MistralOCRClient.
    """
    def __init__(self, source_folder: str, destination_folder: str, ocr_client: MistralOCRClient):
        """
        Initialise the PDF processor.

        Args:
            source_folder (str): Directory containing PDF files.
            destination_folder (str): Directory where OCR results will be saved.
            ocr_client (MistralOCRClient): An instance of the OCR client.
        """
        self.source_folder = Path(source_folder)
        self.destination_folder = Path(destination_folder)
        self.ocr_client = ocr_client
        
        # Create destination folder if it doesn't exist.
        self.destination_folder.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(level=logging.INFO)
    
    def _extract_and_save_images(self, ocr_result, pdf_stem):
        """
        Extract base64 encoded images from OCR result and save them as binary files.
        
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
            updated_page = self._serialize_ocr_result(page)
            
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
                            
                            logging.info(f"Extracted image saved to {img_path}")
                        except Exception as e:
                            logging.error(f"Error saving image {img_filename}: {e}")
            
            updated_result.append(updated_page)
        
        return updated_result
    
    def _serialize_ocr_result(self, obj):
        """
        Convert OCR result objects to serializable dictionaries.
        """
        if hasattr(obj, '__dict__'):
            # For custom objects with __dict__ attribute
            result = {}
            for key, value in obj.__dict__.items():
                # Skip private attributes
                if not key.startswith('_'):
                    if isinstance(value, list):
                        result[key] = [self._serialize_ocr_result(item) for item in value]
                    else:
                        result[key] = self._serialize_ocr_result(value)
            return result
        elif isinstance(obj, list):
            return [self._serialize_ocr_result(item) for item in obj]
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
            logging.info(f"Deleted source file: {file_path}")
        except Exception as e:
            logging.error(f"Error deleting file {file_path}: {e}")

    def process_pdfs(self):
        """
        Iterate through PDF files in the source folder, upload them, process them via OCR,
        and save the results as JSON files in the destination folder.
        """
        pdf_files = list(self.source_folder.glob("*.pdf"))
        if not pdf_files:
            logging.info("No PDF files found in the source folder.")
            return
        
        for pdf_file in pdf_files:
            try:
                logging.info(f"Uploading file: {pdf_file.name}")
                # Step 1: Upload the PDF file and get the file_id
                uploaded_file = self.ocr_client.upload_pdf(str(pdf_file))
                file_id = uploaded_file.id
                logging.info(f"File uploaded successfully. File ID: {file_id}")
                
                # Step 2: Get the signed URL using the file_id
                signed_url_response = self.ocr_client.get_signed_url(file_id)
                signed_url = signed_url_response.url
                logging.info(f"Retrieved signed URL for processing")
                
                # Step 3: Process OCR with the signed URL
                logging.info(f"Processing OCR for file: {pdf_file.name}")
                ocr_result = self.ocr_client.ocr_pdf(signed_url)
                
                # Extract and save images, then serialize the OCR result
                extracted_result = self._extract_and_save_images(ocr_result.pages, pdf_file.stem)
                
                # Save the serialized OCR result to the destination folder
                output_file = self.destination_folder / (pdf_file.stem + ".json")
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(extracted_result, f, indent=4)
                logging.info(f"OCR result saved to {output_file}")
                
                # Delete the source PDF file after successful processing
                self._delete_source_file(pdf_file)
            except Exception as e:
                logging.error(f"Error processing {pdf_file.name}: {e}")
