import os
from pathlib import Path
from mistral import Mistral

class MistralAPIClient:
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

    def upload_pdf(self, file_path: str) -> str:
        """
        Upload a PDF file to the Mistal API for OCR processing.

        Args:
            file_path (str): Path to the PDF file.

        Returns:
            str: The signed URL for the uploaded PDF.
        """
        with open(file_path, "rb") as file:
            response = self.client.files.upload(
                file={
                    "file_name": Path(file_path).name,
                    "content": file,
                },
                purpose="ocr"
            )
        # Assume response is a dictionary with a 'url' key or an object with an attribute 'url'
        signed_url = response.get("url") if isinstance(response, dict) else getattr(response, "url", None)
        if not signed_url:
            raise ValueError("Upload did not return a signed URL.")
        return signed_url

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
