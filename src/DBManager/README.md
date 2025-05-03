# MongoDB Database Schema - WJEC Exam Paper Processor

This document outlines the MongoDB database schema used for storing and managing WJEC exam papers and mark schemes.

## Overview

The database comprises one main collection:

1. **documents** - Stores original document files and OCR results

## Collection Details

### Documents Collection

Stores original document files and their OCR processing results.

#### Schema

```javascript
{
  "_id": ObjectId,                      // MongoDB generated document ID
  "document_id": String,                // Unique document identifier (hash of PDF, indexed, unique)
  "document_type": String,              // Type of document (e.g., "Question Paper", "Mark Scheme")
  "pdf_binary": Binary,                 // Copy of the original PDF
  "ocr_json": Object                    // The OCRed JSON content
}
```

#### Indexes

- `{ 'document_id': 1 }` - Unique index for document identification

## Environment Configuration

The database connection requires the following environment variables:

- `MONGODB_URI`: MongoDB Atlas connection string
- `MONGODB_DATABASE_NAME`: Name of the database to connect to
- `MONGODB_TIMEOUT_MS`: Connection timeout in milliseconds (optional, default: 5000)

## Notes

- All dates are stored in UTC format

# MongoDB Integration for WJEC Exam Paper Processor

This module provides functionality for integrating MongoDB into the WJEC Exam Paper Processor, creating a database-driven workflow for storing and managing exam metadata.

## Overview

The `DBManager` class enables storing and retrieving document data in MongoDB. It supports both individual document operations and bulk processing for improved performance.

## Features

- MongoDB connection management with environment variable support
- Document storage and retrieval
- Duplicate detection and prevention
- Bulk operations for efficient processing
- Graceful error handling with fallback to file-based storage
- Collection management and database initialization

## Usage

### Environment Variables

The following environment variables are used to configure the MongoDB connection:

- `MONGODB_URI`: MongoDB connection string (required)
- `MONGODB_DATABASE_NAME`: Name of the database to connect to (default: "wjec_exams")
- `MONGODB_TIMEOUT_MS`: Connection timeout in milliseconds (default: 5000)

### Basic Example

```python
from src.DBManager.db_manager import DBManager

# Create a DB manager (uses MONGODB_URI env var by default)
db_manager = DBManager()

# Store metadata
metadata = {
    "subject": "Computer Science",
    "qualification": "A-Level",
    "year": 2023,
    "season": "Summer",
    "unit": 3,
    "document_type": "Question Paper"
}

# Save to database
document_id = db_manager.save_exam_metadata(metadata)

# Retrieve from database
retrieved = db_manager.get_exam_metadata(document_id)

# Close connection when done
db_manager.disconnect()
```

### Bulk Operations

```python
# Process multiple documents efficiently
metadata_list = [
    {
        "subject": "Computer Science",
        "qualification": "A-Level",
        "year": 2023,
        "season": "Summer",
        "unit": 3,
        "document_type": "Question Paper"
    },
    {
        "subject": "Computer Science",
        "qualification": "A-Level",
        "year": 2023,
        "season": "Summer",
        "unit": 3,
        "document_type": "Mark Scheme"
    }
]

# Save multiple documents in a single operation
document_ids = db_manager.bulk_save_exam_metadata(metadata_list)
```

## Dependencies

The module requires the following packages:

```
pymongo
python-dotenv
```

## Graceful Degradation

If `pymongo` is not installed or MongoDB is unavailable, the module will fall back to file-based storage with appropriate warnings.
