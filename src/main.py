import os
from mistralOCRClient import MistralOCRClient

from pdfOcrProcessor import PDF_OCR_Processor

def main():
    """
    Main function to run the PDF OCR processing.
    """
    # Retrieve the source and destination folders from environment variables.
    source_folder = os.environ.get("SOURCE_FOLDER")
    if not source_folder:
        raise EnvironmentError("SOURCE_FOLDER environment variable not set.")
    
    destination_folder = os.environ.get("DESTINATION_FOLDER")
    if not destination_folder:
        raise EnvironmentError("DESTINATION_FOLDER environment variable not set.")
    
    # Retrieve the Mistal API key from the environment.
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise EnvironmentError("MISTRAL_API_KEY environment variable not set.")
    
    
    # Initialise the Mistal OCR client using the MistalAI Python library.
    ocr_client = MistralOCRClient(api_key=api_key)
    
    # Initialise and run the PDF OCR processor.
    processor = PDF_OCR_Processor(source_folder, destination_folder, ocr_client)
    processor.process_pdfs()

if __name__ == "__main__":
    main()
