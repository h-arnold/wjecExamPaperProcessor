# Index Update Tool

## Overview

The Index Update Tool is a utility script for managing the master index of exam documents in the WJEC Exam Paper Processor system. It provides several key functions:

1. Adding missing `exam_season` field to index entries
2. Organizing and relocating index files and referenced documents
3. Maintaining relationships between related documents (e.g., question papers and mark schemes)

## Features

- **Exam Season Detection**: Automatically adds the exam season (Summer/Winter) to index entries using:
  - Direct extraction from metadata files (preferred method)
  - Intelligent inference from document IDs and naming patterns
  - Date pattern analysis from document codes

- **File Organization**: 
  - Copy or move index and all referenced files to a target directory
  - Maintain directory structure during relocation
  - Update file paths in the index to reflect new locations

- **Error Handling**:
  - Graceful handling of missing or inaccessible files
  - Detailed reporting of processing results

## Usage

### Basic Usage

Update exam_season fields in an existing index:

```bash
python update_index.py --index path/to/your/index.json
```

### Copy Files to New Location

Update index and copy all referenced files to a new directory:

```bash
python update_index.py --index path/to/your/index.json --target-dir /path/to/new/location
```

### Move Files to New Location

Update index and move all referenced files to a new directory:

```bash
python update_index.py --index path/to/your/index.json --target-dir /path/to/new/location --move
```

### All Options

```bash
python update_index.py --help
```

This will display all available command-line options:

```
usage: update_index.py [-h] [--index INDEX] [--target-dir TARGET_DIR] [--move] [--verbose]

Update index.json with exam_season field and optionally move/copy files

optional arguments:
  -h, --help            show this help message and exit
  --index INDEX         Path to the index file (default: test_index.json)
  --target-dir TARGET_DIR
                        Target directory for index and related files (default: Index)
  --move                Move files instead of copying them
  --verbose, -v         Show verbose output
```

## How It Works

1. **Loading the Index**: The script first loads the specified index file
2. **Updating Exam Season**: For each document in the index:
   - Check if exam_season is missing
   - Try to extract it from the document's metadata file
   - Fall back to inference from document ID if metadata extraction fails
3. **File Relocation** (if target directory specified):
   - Update all file paths in the index
   - Create target directory structure
   - Copy/move all referenced files
   - Save updated index in the target location

## Examples

### Example 1: Update Existing Index

```bash
python update_index.py --index test_index.json
```

Output:
```
Loaded index with 42 documents
Updated 0 documents with missing exam_season field
- 0 updated from metadata files
- 0 inferred from document IDs
Successfully updated index file at test_index.json
```

### Example 2: Copy Index and Files to New Location

```bash
python update_index.py --index test_index.json --target-dir ./organized_exams
```

Output:
```
Loaded index with 42 documents
Updated 0 documents with missing exam_season field
- 0 updated from metadata files
- 0 inferred from document IDs
Moving/copying files to target directory: ./organized_exams
Copying 84 files to target directory...
Successfully copied 84 of 84 files
Saved index to ./organized_exams/test_index.json
```

## Troubleshooting

- **Missing files**: If source files are missing, the script will display warnings but continue processing the rest of the files
- **Permission errors**: Make sure you have appropriate read/write permissions for both source and target directories
- **Index not found**: Double-check the path to your index file

## Further Development

Potential improvements for future versions:

- Support for merging multiple indexes
- Advanced filtering of documents to include/exclude
- Interactive mode for manual validation of exam seasons
- Batch processing of multiple index files
