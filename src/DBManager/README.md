# MongoDB Database Schema - WJEC Exam Paper Processor

This document outlines the MongoDB database schema used for storing and managing WJEC exam papers and mark schemes.

## Overview

The database comprises several collections:

1. **documents** - Stores original document files and OCR results
2. **specifications** - Stores curriculum specifications
3. **Subject-specific collections** - Dynamically created collections for each subject (e.g., `computer_science`)

## Collection Details

### Documents Collection

Stores original document files and their OCR processing results.

#### Schema

```javascript
{
  "_id": ObjectId,                      // MongoDB generated document ID
  "document_id": String,                // Unique document identifier (hash of PDF, indexed, unique)
  "document_type": String,              // Type of document (e.g., "Question Paper", "Mark Scheme")
  "pdf_file_id": String,                // GridFS ID for the stored PDF
  "pdf_filename": String,               // Original filename of the PDF
  "pdf_upload_date": Date,              // Timestamp of PDF upload
  "ocr_storage": String,                // GridFS ID for OCR data (if stored externally)
  "ocr_upload_date": Date,              // Timestamp of OCR processing
  "images": Array,                      // Array of image file IDs
  "processed": Boolean                  // Flag indicating processing status
}
```

#### Indexes

- `{ 'document_id': 1 }` - Unique index for document identification

### Subject-specific Collections

Collections named after subjects (e.g., `computer_science`) that store exam metadata.

#### Schema

```javascript
{
  "_id": ObjectId,                      // MongoDB generated document ID
  "Exam ID": String,                    // Unique exam identifier
  "Qualification": String,              // Level of qualification (AS-Level, A2-Level, GCSE)
  "Year": Number,                       // The year when the exam was published
  "Subject": String,                    // The subject of the exam
  "Unit Number": String,                // The unit or paper number
  "Exam Season": String,                // Season when the exam takes place
  "Exam Length": String,                // Duration of the exam
  "Information for Candidates": String, // Optional instructions for candidates
  "Information for Examiners": String,  // Optional instructions for examiners
  "Total Marks": Number                 // Optional total marks available
}
```

### Specifications Collection

Stores curriculum specifications for different qualifications and subjects.

#### Schema

```javascript
{
  "_id": ObjectId,                     // MongoDB generated document ID
  "qualification": String,             // Level of qualification (AS-Level, A2-Level, GCSE)
  "subject": String,                   // The subject name
  "year_introduced": Number,           // Year the specification was introduced
  "version": String,                   // Version identifier
  "units": Array,                      // Array of unit objects
  "imported_at": Date                  // Timestamp of import
}
```

## Environment Configuration

The database connection requires the following environment variables:

- `MONGODB_URI`: MongoDB Atlas connection string
- `MONGODB_DATABASE_NAME`: Name of the database to connect to (default: "wjec_exams")
- `MONGODB_TIMEOUT_MS`: Connection timeout in milliseconds (optional, default: 5000)

## Notes

- All dates are stored in UTC format
- GridFS is used for storing PDF files, OCR results, and images

# MongoDB Integration for WJEC Exam Paper Processor

This module provides functionality for integrating MongoDB into the WJEC Exam Paper Processor, creating a database-driven workflow for storing and managing exam metadata.

## Architecture

The database integration follows the Repository pattern with three main components:

1. **DBManager** - Singleton class that manages database connections and provides low-level operations
2. **BaseRepository** - Generic base class that implements common CRUD operations
3. **Specialized Repositories** - Classes like `ExamRepository` and `DocumentRepository` that handle domain-specific database operations

## DBManager Features

- MongoDB connection management with environment variable support
- Singleton pattern ensuring consistent database connections
- Graceful error handling with appropriate logging
- GridFS support for binary file storage
- Collection management and database initialisation
- Generic query execution methods for repositories

## Repository Pattern

The repository pattern provides an abstraction layer between the domain models and database operations:

- **BaseRepository**: Implements generic CRUD operations with proper error handling
- **ExamRepository**: Handles exam-specific database operations
- **DocumentRepository**: Manages document storage and retrieval

### Example: Using ExamRepository

```python
from src.DBManager.exam_repository import ExamRepository
from src.Models.exam import Exam, Qualification, ExamSeason

# Create repository
exam_repo = ExamRepository()

# Check if exam exists
exists = exam_repo.check_exam_exists("CS_AS-Level_2023_Summer_1", "Computer Science")

# Get exam by ID
exam = exam_repo.get_exam("CS_AS-Level_2023_Summer_1", "Computer Science")

# Get exams by criteria
criteria = {
    "Year": 2023,
    "Qualification": "AS-Level",
    "Exam Season": "Summer"
}
exams = exam_repo.get_exams_by_criteria("Computer Science", criteria)

# Create or update exam
new_exam = Exam(
    exam_id="CS_AS-Level_2023_Summer_1",
    qualification=Qualification.AS_LEVEL,
    year=2023,
    subject="Computer Science",
    unit_number="1",
    exam_season=ExamSeason.SUMMER,
    exam_length="1 hour 30 minutes",
    total_marks=60
)
success = exam_repo.create_exam(new_exam)
```

### Example: Using DocumentRepository

```python
from src.DBManager.document_repository import DocumentRepository
from pathlib import Path
import datetime
from datetime import UTC

# Create repository
doc_repo = DocumentRepository()

# Store a PDF document
pdf_path = Path("/path/to/exam_paper.pdf")
document_id = "hash123"
document_type = "Question Paper"
now = datetime.datetime.now(UTC)

# Store PDF in GridFS and create document record
pdf_id = doc_repo.store_pdf_in_gridfs(pdf_path, document_id, document_type)
success = doc_repo.create_document_from_pdf(document_id, document_type, pdf_path.name, pdf_id, now)

# Retrieve document
document = doc_repo.get_document(document_id)

# Update document processing status
success = doc_repo.update_document(document_id, {"processed": True})
```

## Implementation Details

### DBManager

The `DBManager` class is implemented as a singleton to ensure only one database connection is maintained throughout the application. It provides methods for:

- Connecting to MongoDB
- Managing collections
- Executing queries
- Handling GridFS operations
- Initialising the database structure

### BaseRepository

The `BaseRepository` class provides common CRUD operations for repositories:

- `exists()` - Check if a document exists
- `get_by_id()` - Retrieve a document by ID
- `get_many()` - Retrieve documents matching criteria
- `create_or_update()` - Create or update a document
- `update()` - Update a document
- `delete()` - Delete a document
- `get_all()` - Retrieve all documents in a collection

## Dependencies

The module requires the following packages:

```
pymongo
python-dotenv
```

## Graceful Degradation

If `pymongo` is not installed or MongoDB is unavailable, the DBManager will log appropriate warnings and fall back to file-based storage when possible.
