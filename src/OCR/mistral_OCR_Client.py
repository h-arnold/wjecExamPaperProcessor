import os
import logging
from pathlib import Path
from mistralai import Mistral
import io

class MistralOCRClient:
    """
    A client for interacting with the Mistal OCR API using the MistalAI Python library.
    """
    def __init__(self, api_key: str, model: str = "mistral-ocr-latest"):
        """
        Initialise the OCR client.

        Args:
            api_key (str): The Mistal API key.
            model (str): The OCR model to use. Default is 'mistral-ocr-latest'.
        """
        self.client = Mistral(api_key=api_key)
        self.model = model

    def upload_pdf(self, file, filename="document.pdf") -> str:
        """
        Upload a PDF file to the Mistral API for OCR processing.

        Args:
            file (bytes | BytesIO): The PDF file content as bytes or BytesIO object
            filename (str, optional): Name to use for the file. Defaults to "document.pdf"

        Returns:
            str: Response from the Mistral API containing file information

        Raises:
            ValueError: If file content is empty or upload fails
        """
        logger = logging.getLogger(__name__)
        
        try:
            # Convert to bytes if needed
            if hasattr(file, 'read'):
                file_content = file.read()
            else:
                file_content = file

            if not file_content:
                raise ValueError("File content is empty")
            
            logger.debug(f"Uploading file with name {filename} to Mistral OCR API")
            
            # Upload file according to the API documentation
            # The API expects raw bytes for the content, not a file-like object
            response = self.client.files.upload(file={
                "file_name": filename,
                "content": open(file_content, "rb")},
                purpose="ocr")
            
            logger.debug(f"File uploaded successfully, received ID: {response.id}")
            return response

        except Exception as e:
            logger.error(f"Failed to upload PDF: {str(e)}")
            raise ValueError(f"Failed to upload PDF: {str(e)}")

    def get_signed_url(self, file_id: str):
        """
        Get a signed URL for an uploaded file.

        Args:
            file_id (str): The ID of the uploaded file.

        Returns:
            object: Response containing the signed URL for the file.
        """
        return self.client.files.get_signed_url(file_id=file_id)

    def ocr_pdf(self, signed_url: str, include_image_base64: bool = True) -> dict:
        """
        Perform OCR on a PDF document using its signed URL.

        Args:
            signed_url (str): The signed URL of the uploaded PDF.
            include_image_base64 (bool): Whether to include base64 image data in the response.

        Returns:
            dict: The OCR result as a JSON/dictionary.
        """
        return self.client.ocr.process(
            model=self.model,
            document={
                "type": "document_url",
                "document_url": signed_url,
            },
            include_image_base64=include_image_base64
        )
