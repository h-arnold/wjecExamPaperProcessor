# MongoDB Database Schema - WJEC Exam Paper Processor

This document outlines the MongoDB database schema used for storing and managing WJEC exam papers, mark schemes, and subject specifications.

## Overview

The database comprises three main collections:

1. **exams** - Stores processed exam papers and mark schemes
2. **specifications** - Stores subject specifications with hierarchical structure
3. **spec_coverage** - Tracks specification coverage across different exam papers

## Collection Details

### Exams Collection

Stores individual exam papers with their questions and mark schemes.

#### Schema

```javascript
{
  "_id": ObjectId,                      // MongoDB generated document ID
  "examId": String,                     // Unique exam identifier (indexed, unique)
  "subject": String,                    // Subject name (e.g., "Computer Science")
  "qualification": String,              // Qualification level (e.g., "AS-Level", "A2-Level")
  "year": Number,                       // Year of exam publication
  "season": String,                     // Exam season (e.g., "Summer", "Winter")
  "unit": String,                       // Unit identifier (e.g., "Unit 1", "Unit 2")
  "exam_board": String,                 // Exam board (typically "WJEC")
  "paper_type": String,                 // Type of paper (e.g., "Question Paper", "Mark Scheme")
  "questions": [                        // Array of questions
    {
      "question_number": String,        // Question identifier (e.g., "1a", "2bi")
      "question_text": String,          // Full text of the question
      "marks": Number,                  // Marks allocated for the question
      "mark_scheme": String,            // Mark scheme for the question
      "spec_refs": [String],            // Array of specification references (e.g., "1.2.3")
      "images": [                       // Array of images associated with the question
        {
          "url": String,                // URL or path to image
          "caption": String,            // Optional image caption
          "page": Number                // Page number where image appears
        }
      ],
      "difficulty_level": Number,       // Optional AI-estimated difficulty (1-5)
      "keywords": [String]              // Keywords extracted from the question
    }
  ],
  "metadata": {                         // Additional metadata
    "total_marks": Number,              // Total marks for the paper
    "time_allowed": String,             // Time allowed for the exam
    "source_file": String,              // Original PDF filename
    "processed_date": Date              // Date when processed
  }
}
```

#### Indexes

- `{ 'subject': 1, 'year': 1, 'season': 1 }` - For filtering by subject, year, and season
- `{ 'examId': 1 }` - Unique index for exam identification
- `{ 'questions.spec_refs': 1 }` - For finding questions by specification reference
- Text index on `{ 'subject': 'text', 'questions.question_text': 'text', 'questions.mark_scheme': 'text' }` - For full-text search

### Specifications Collection

Stores subject specifications with their hierarchical structure of units, sections, and items.

#### Schema

```javascript
{
  "_id": ObjectId,                      // MongoDB generated document ID
  "qualification": String,              // Qualification level (e.g., "AS-Level")
  "subject": String,                    // Subject name (e.g., "Computer Science")
  "year_introduced": Number,            // Year the specification was introduced
  "version": String,                    // Version identifier
  "units": [                            // Array of units
    {
      "unit_number": String,            // Unit identifier (e.g., "1", "2")
      "unit_name": String,              // Name of the unit
      "sections": [                     // Array of sections within the unit
        {
          "section_number": String,     // Section identifier (e.g., "1.1", "2.3")
          "section_name": String,       // Name of the section
          "items": [                    // Array of specification items
            {
              "spec_ref": String,       // Specification reference (e.g., "1.1.1")
              "description": String,    // Full description of the specification point
              "keywords": [String]      // Keywords extracted from the description
            }
          ]
        }
      ]
    }
  ],
  "imported_at": Date                   // Date when the specification was imported
}
```

#### Indexes

- `{ 'qualification': 1, 'subject': 1 }` - For filtering by qualification and subject
- `{ 'units.sections.items.spec_ref': 1 }` - For finding specific specification references
- `{ 'units.sections.items.keywords': 1 }` - For keyword-based searches

### Spec Coverage Collection

Tracks how frequently each specification point is covered in exams.

#### Schema

```javascript
{
  "_id": ObjectId,                      // MongoDB generated document ID
  "qualification": String,              // Qualification level
  "subject": String,                    // Subject name
  "spec_ref": String,                   // Specification reference
  "coverage_frequency": Number,         // Number of times this spec point appears in exams
  "exams": [                            // Array of exams covering this spec point
    {
      "examId": String,                 // Exam identifier
      "year": Number,                   // Year of the exam
      "season": String,                 // Season of the exam
      "question_numbers": [String]      // Question numbers that cover this spec point
    }
  ],
  "last_updated": Date                  // Date when the coverage was last updated
}
```

#### Indexes

- `{ 'qualification': 1, 'subject': 1, 'spec_ref': 1 }` - Unique index for specification reference
- `{ 'coverage_frequency': 1 }` - For sorting by coverage frequency

## Relationships

- **exams ↔ specifications**: Questions in exams reference specification points via `questions.spec_refs`
- **specifications ↔ spec_coverage**: Specification points in `specifications` collection are tracked in `spec_coverage` collection
- **exams ↔ spec_coverage**: Exams that cover specific specification points are listed in `spec_coverage.exams`

## Usage Examples

### Finding Exams by Specification Reference

```javascript
db.exams.find({ 'questions.spec_refs': '1.2.3' })
```

### Finding Specification Points with Low Coverage

```javascript
db.spec_coverage.find({ 'coverage_frequency': { $lt: 3 } }).sort({ 'coverage_frequency': 1 })
```

### Finding Questions Related to a Specific Topic

```javascript
db.exams.find(
  { $text: { $search: "binary tree traversal" } },
  { score: { $meta: "textScore" } }
).sort({ score: { $meta: "textScore" } })
```

## Environment Configuration

The database connection requires the following environment variables:

- `MONGODB_URI`: MongoDB Atlas connection string
- `MONGODB_DATABASE_NAME`: Name of the database to connect to
- `MONGODB_TIMEOUT_MS`: Connection timeout in milliseconds (optional, default: 5000)

## Notes

- All dates are stored in UTC format
- Text indexes support full-text search for finding relevant questions
- The system automatically updates coverage statistics when new exams are imported
