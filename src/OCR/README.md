# OCR Processing Module

## Overview

The OCR (Optical Character Recognition) processing module provides functionality to scan PDF exam papers and extract structured text and images. This module supports both filesystem storage and MongoDB hybrid storage for the OCR results.

## Key Components

### MistralOCRClient

Client for the Mistral AI OCR API that handles:
- PDF file uploads
- Retrieving signed URLs for processing
- Executing OCR on PDF documents
- Processing OCR results with text and images

### PDF_OCR_Processor

Main processor class that:
- Processes PDF files from a source directory
- Manages OCR extraction using the MistralOCRClient
- Determines document types automatically (Question Paper or Mark Scheme)
- Supports both filesystem and MongoDB hybrid storage

## Storage Options

### Filesystem Storage (Legacy)

Stores OCR results as JSON files in a specified destination folder with:
- Extracted images saved to a separate subfolder
- References to image paths included in the JSON

### MongoDB Hybrid Storage (Default)

Implements an intelligent hybrid storage approach:
- PDFs are stored in GridFS (MongoDB's solution for large files)
- OCR JSON results are:
  - Stored directly in the MongoDB document if small (<5MB)
  - Stored in GridFS if large (>5MB)
- Images from OCR extraction are:
  - Stored inline in MongoDB if small (<500KB)
  - Stored in GridFS if large (>500KB)

This hybrid approach optimises both storage efficiency and query performance.

## Configuration

The module is configured through environment variables:
- `SOURCE_FOLDER`: Directory containing PDF files to process
- `DESTINATION_FOLDER`: Directory where OCR results will be saved (if using filesystem storage)
- `MISTRAL_API_KEY`: API key for Mistral AI OCR services
- `MONGODB_URI`: MongoDB connection string (for MongoDB storage)
- `MONGODB_DATABASE_NAME`: Name of the MongoDB database (for MongoDB storage)
- `USE_FILESYSTEM_STORAGE`: Set to "True" to use legacy filesystem storage (default: "False")

## Usage

### Command-Line Interface

Run the OCR processor from the command line:

```bash
python -m src.OCR.main
```

### Programmatic Usage

```python
from src.OCR.mistral_OCR_Client import MistralOCRClient
from src.OCR.pdf_Ocr_Processor import PDF_OCR_Processor
from src.DBManager.db_manager import DBManager

# Create OCR client
ocr_client = MistralOCRClient(api_key="your_mistral_api_key")

# Create DB manager (for MongoDB storage)
db_manager = DBManager(connection_string="mongodb://...", database_name="your_db")

# Create PDF processor with MongoDB storage (default)
processor = PDF_OCR_Processor(
    source_folder="source_pdf",
    destination_folder="ocr_results",
    ocr_client=ocr_client,
    use_mongodb=True,
    db_manager=db_manager
)

# Process PDF files
processed_documents = processor.process_pdfs()
```

## Error Handling

The module includes comprehensive error handling:
- Connection issues with MongoDB or Mistral API
- File I/O errors
- PDF processing errors
- Serialisation errors
- GridFS storage failures

All errors are logged with appropriate detail level.

## Database Schema (MongoDB)

When using MongoDB storage, documents are stored with the following structure:

```
{
    "document_id": "hash_of_pdf",
    "document_type": "Question Paper"/"Mark Scheme",
    "pdf_file_id": "gridfs_id",
    "pdf_filename": "original_filename.pdf",
    "pdf_upload_date": ISODate("2025-05-03T..."),
    "ocr_storage": "inline"/"gridfs",
    "ocr_upload_date": ISODate("2025-05-03T..."),
    "ocr_json": {...}  // Only if ocr_storage is "inline"
    "ocr_file_id": "gridfs_id",  // Only if ocr_storage is "gridfs"
    "images": [
        {
            "image_id": "img_p1_1",
            "page": 1,
            "index": 1,
            "format": "jpeg",
            "storage": "inline",
            "data": "base64_data"  // Only for small images
        },
        {
            "image_id": "img_p1_2",
            "page": 1, 
            "index": 2,
            "format": "png",
            "storage": "gridfs",
            "file_id": "gridfs_id"  // For large images
        }
    ]
}
```