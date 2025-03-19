import os
import json
import logging
from pathlib import Path
from mistral_ocr_client import MistralOCRClient

class PDFOCRProcessor:
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
                signed_url = self.ocr_client.upload_pdf(str(pdf_file))
                logging.info(f"File uploaded successfully. Signed URL: {signed_url}")
                
                logging.info(f"Processing OCR for file: {pdf_file.name}")
                ocr_result = self.ocr_client.ocr_pdf(signed_url)
                
                # Save the OCR result to the destination folder.
                output_file = self.destination_folder / (pdf_file.stem + ".json")
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(ocr_result, f, indent=4)
                logging.info(f"OCR result saved to {output_file}")
            except Exception as e:
                logging.error(f"Error processing {pdf_file.name}: {e}")
