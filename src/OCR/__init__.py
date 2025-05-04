"""
OCR processing module for WJEC Exam Paper Processor.

This module provides functionality for OCR processing of PDF exam papers using
the Mistral AI OCR API. It includes components for uploading PDFs, processing them
through OCR, and storing results in MongoDB.

Classes:
    MistralOCRClient: Client for interacting with Mistral's OCR API
    PDF_OCR_Processor: Handles PDF processing workflow and storage
"""

from .mistral_OCR_Client import MistralOCRClient
from .pdf_Ocr_Processor import PDF_OCR_Processor
from .main import main

__all__ = [
    'MistralOCRClient',
    'PDF_OCR_Processor',
    'main'
]
