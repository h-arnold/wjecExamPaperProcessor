# IndexManager

## Overview

The `IndexManager` class is a comprehensive solution for managing, transforming, and enhancing the index of WJEC exam documents. It handles the entire workflow from creating a flat index of documents to generating a hierarchical structure that organizes papers by subject, year, qualification, and unit.

## Features

- **Document Indexing**: Create and maintain an index of exam documents with comprehensive metadata
- **Unit Number Detection**: Automatically extract unit numbers from document IDs and titles
- **Relationship Detection**: Identify relationships between question papers and mark schemes
- **Hierarchical Transformation**: Convert flat document lists into a structured hierarchy
- **Metadata Enhancement**: Enhance exam entries with metadata from document files
- **Conflict Resolution**: Handle metadata conflicts with interactive or automated resolution
- **Search Functionality**: Find documents based on metadata criteria or text queries

## Usage

### Basic Usage

```python
from src.IndexManager import IndexManager

# Initialize with path to the flat index
index_manager = IndexManager("Index/index.json")

# Run the complete workflow (update, transform, and enhance)
index_manager.run_full_process(
    output_path="Index/hierarchical_index.json",
    interactive=True  # Set to False for automatic conflict resolution
)
```

### Adding a New Document

```python
# Add or update a document in the index
metadata = {
    "Type": "Question Paper",
    "Year": 2023,
    "Qualification": "GCE A Level",
    "Subject": "Computer Science",
    "Exam Paper": "Unit 3: Programming and System Development",
    "Exam Season": "Summer"
}

index_manager.update_index(
    metadata,
    content_path="ocr_results/s23-1500u30-1.json",
    metadata_path="ocr_results/metadata/s23-1500u30-1-metadata.json"
)
```

### Document Relationships

```python
# Find related documents (e.g., mark scheme for a question paper)
related_docs = index_manager.find_related_documents("s23-1500u30-1")

# Find related documents by unit number, year, and qualification
related_by_unit = index_manager.find_related_by_unit("s23-1500u30-1")
```

### Updating the Index

```python
# Update unit numbers for all documents
updated_count = index_manager.update_unit_numbers()

# Update relationships between documents
relationships = index_manager.update_all_document_relations()

# Sort documents by subject, year, qualification, and unit number
sorted_docs = index_manager.sort_index()
```

### Transforming to Hierarchical Structure

```python
# Transform flat index to hierarchical structure
hierarchical = index_manager.transform_to_hierarchical(
    output_path="Index/hierarchical_index.json",
    interactive=False
)
```

### Enhancing with Metadata

```python
# Enhance existing hierarchical structure with document metadata
enhanced = index_manager.enhance_hierarchical_structure(
    hierarchical_path="Index/hierarchical_index.json",
    interactive=False
)
```

### Document Search

```python
# Search by criteria
criteria_results = index_manager.search_documents(
    criteria={"subject": "Computer Science", "year": 2023}
)

# Search by text query
text_results = index_manager.search_documents(
    query="Unit 3"
)
```

## Command-Line Interface

The module also provides a command-line interface through `main.py`:

```bash
python -m src.IndexManager.main [options]
```

### Options

- `--input PATH`: Path to input flat index file (default: Index/index.json)
- `--output PATH`: Path for output hierarchical index file (default: Index/hierarchical_index.json)
- `--non-interactive`: Run in non-interactive mode (automatically select first option for conflicts)
- `--update-only`: Only update unit numbers and relationships (skip transformation and enhancement)
- `--transform-only`: Only transform the structure (skip enhancement)
- `--enhance-only`: Only enhance existing hierarchical structure (skip updating and transformation)
- `--skip-metadata`: Skip enhancing the structure with document metadata

## Data Structures

### Flat Index

The flat index is a JSON file with a list of document entries:

```json
{
  "documents": [
    {
      "id": "s23-1500u30-1",
      "type": "Question Paper",
      "year": 2023,
      "qualification": "GCE A Level",
      "subject": "Computer Science",
      "exam_paper": "Unit 3: Programming and System Development",
      "exam_season": "Summer",
      "content_path": "ocr_results/s23-1500u30-1.json",
      "metadata_path": "ocr_results/metadata/s23-1500u30-1-metadata.json",
      "unit_number": 3,
      "related_documents": ["s23-1500u30-1-ms"]
    }
  ]
}
```

### Hierarchical Index

The hierarchical index organizes documents by subject, year, qualification, and unit:

```json
{
  "subjects": {
    "Computer Science": {
      "years": {
        "2023": {
          "qualifications": {
            "GCE A Level": {
              "exams": {
                "Unit 3": {
                  "unit_number": 3,
                  "name": "Programming and System Development",
                  "exam_length": "2 hours",
                  "total_marks": 100,
                  "documents": {
                    "Question Paper": [
                      { "id": "s23-1500u30-1", "content_path": "...", "metadata_path": "..." }
                    ],
                    "Mark Scheme": [
                      { "id": "s23-1500u30-1-ms", "content_path": "...", "metadata_path": "..." }
                    ]
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

## Implementation Details

### Unit Number Detection

The `IndexManager` uses regular expressions to extract unit numbers from document IDs and exam paper titles. It recognizes patterns such as:

- "Unit 3" or "unit 3" or "Unit3"
- "u30-" in exam codes like "1500u30-1"
- "U30-" in exam codes like "1500U30-1"

### Document Relationship Detection

Documents are related using two approaches:
1. **Pattern matching**: Using filename patterns (e.g., s23-2500u20-1a.json and s23-2500u20-1-ms.json)
2. **Metadata matching**: Matching unit numbers, years, subjects, and qualifications

## Error Handling

The `IndexManager` includes error handling for:
- Missing index files (creates new ones if needed)
- JSON parsing errors
- File I/O errors
- Missing metadata files

## Contributing

When extending or modifying the `IndexManager`, please:
1. Maintain backward compatibility with existing index files
2. Follow the existing code style and documentation standards
3. Add unit tests for new functionality
4. Update this README to reflect significant changes