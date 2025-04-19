# Exam Paper Metadata Extraction System: Design Document and Implementation Plan

## 1. System Overview

The Exam Paper Metadata Extraction System will process OCR-extracted JSON files of WJEC exam papers and mark schemes, extract structured metadata, and organize it using a hybrid approach of individual metadata files with a master index. The system will be modular, adhering to DRY principles, and will allow flexibility in choosing LLM providers for metadata extraction.

## 2. Architecture Design

### 2.1 Directory Structure

```
/workspaces/wjecExamPaperProcessor/
├── ocr_results/                  # OCR JSON files (existing)
├── metadata/                     # Generated metadata 
files
│   ├── question_papers/          # Question paper metadata
│   └── mark_schemes/             # Mark scheme metadata
├── index.json                    # Master index file 
└── src/                          # Source code
    ├── document_processor.py     # Main document processing logic
    ├── metadata_extractor.py     # Metadata extraction functionality
    ├── file_manager.py           # File handling operations
    ├── index_manager.py          # Index management functionality
    ├── llm_client/               # LLM client implementations
    │   ├── __init__.py           
    │   ├── base_client.py        # Abstract base LLM client
    │   ├── mistral_client.py     # Mistral implementation
    │   └── factory.py            # Factory for creating LLM clients
    └── utils/                    # Utility functions
```

### 2.2 Core Components

#### 2.2.1 Document Processor

Central orchestration component that:

- Handles the end-to-end processing pipeline
- Coordinates between other components
- Provides a high-level API for document processing operations

#### 2.2.2 Metadata Extractor

Responsible for:

- Extracting structured metadata from exam paper content
- Validating metadata against expected schema
- Enriching metadata with system-specific information (like file paths)

#### 2.2.3 File Manager

Handles:

- Reading OCR files
- Writing individual metadata files
- Managing file organization based on document type

#### 2.2.4 Index Manager

Manages the master index file:

- Creating and updating index entries
- Finding relationships between documents
- Providing search capabilities across the corpus

#### 2.2.5 LLM Client

Abstract interface for LLM services:

- Base abstract class defining common interface
- Implementation-specific subclasses (Mistral, OpenAI, etc.)
- Factory for creating appropriate clients

## 3. Component Specifications

### 3.1 Document Processor

```python
class DocumentProcessor:
    def __init__(self, llm_client, file_manager=None, index_manager=None):
        self.llm_client = llm_client
        self.file_manager = file_manager or MetadataFileManager()
        self.index_manager = index_manager or IndexManager()
        
    def process_document(self, ocr_file_path):
        """Process a single document end-to-end"""
        
    def process_directory(self, directory_path, pattern="*.json"):
        """Process all matching documents in a directory"""
        
    def find_related_documents(self, document_id):
        """Find related documents (e.g., mark scheme for a question paper)"""
```

### 3.2 Metadata Extractor

```python
class MetadataExtractor:
    def __init__(self, llm_client):
        self.llm_client = llm_client
        
    def extract_metadata(self, ocr_content, metadata_prompt):
        """Extract metadata from OCR content using the LLM client"""
        
    def enrich_metadata(self, metadata, file_path):
        """Add additional metadata like file path"""
        
    def validate_metadata(self, metadata):
        """Validate metadata structure against expected schema"""
```

### 3.3 File Manager

```python
class MetadataFileManager:
    def __init__(self, base_dir="metadata"):
        self.base_dir = base_dir
        
    def read_ocr_file(self, file_path):
        """Read and parse OCR JSON file"""
        
    def save_metadata(self, metadata, document_id):
        """Save metadata to individual JSON file based on document type"""
        
    def get_metadata(self, document_id):
        """Read metadata from file"""
        
    def get_metadata_path(self, document_id, document_type):
        """Generate the appropriate path for a metadata file"""
```

### 3.4 Index Manager

```python
class IndexManager:
    def __init__(self, index_path="index.json"):
        self.index_path = index_path
        
    def update_index(self, metadata, metadata_file_path):
        """Add or update document in the index"""
        
    def find_related_documents(self, document_id, relation_type=None):
        """Find related documents based on ID patterns and metadata"""
        
    def search_documents(self, criteria):
        """Search documents based on metadata criteria"""
        
    def load_index(self):
        """Load the index from disk"""
        
    def save_index(self):
        """Save the index to disk"""
```

### 3.5 LLM Client

An abstract base class (`LLMClient`) with concrete implementations (e.g., `MistralLLMClient`) and a factory class for creating clients.

## 4. Index Structure

```json
{
  "documents": [
    {
      "id": "s23-2500u20-1a",
      "type": "Question Paper",
      "year": 2023,
      "qualification": "AS-Level",
      "subject": "Computer Science",
      "exam_paper": "Unit 2",
      "content_path": "/workspaces/wjecExamPaperProcessor/ocr_results/s23-2500u20-1a.json",
      "metadata_path": "/metadata/question_papers/s23-2500u20-1a-metadata.json",
      "related_documents": ["s23-2500u20-1-ms"]
    },
    {
      "id": "s23-2500u20-1-ms",
      "type": "Mark Scheme",
      "year": 2023,
      "qualification": "AS-Level",
      "subject": "Computer Science",
      "exam_paper": "Unit 2",
      "content_path": "/workspaces/wjecExamPaperProcessor/ocr_results/s23-2500u20-1-ms.json",
      "metadata_path": "/metadata/mark_schemes/s23-2500u20-1-ms-metadata.json",
      "related_documents": ["s23-2500u20-1a"]
    }
  ]
}
```

## 5. Implementation Plan

### Phase 1: Core Infrastructure

1. **Create project structure**
   - Set up directory structure
   - Create empty module files
   - Add `__init__.py` files for proper imports

2. **Implement LLM Client abstraction**
   - Create base abstract LLM client
   - Implement Mistral-specific client
   - Create factory for client selection

3. **Create MetadataFileManager**
   - Implement file I/O operations
   - Add methods for reading OCR files
   - Add methods for writing metadata files

### Phase 2: Metadata Processing

4. **Build MetadataExtractor**
   - Connect to LLM client
   - Implement metadata extraction logic
   - Add metadata enrichment with file paths
   - Create metadata validation

5. **Create IndexManager**
   - Define index structure
   - Implement CRUD operations for index
   - Add related document detection logic

### Phase 3: Integration and Testing

6. **Implement DocumentProcessor**
   - Create end-to-end processing pipeline
   - Add batch processing capability
   - Implement document relation linking

7. **Create command-line interface**
   - Add argument parsing
   - Implement subcommands for different operations
   - Create configuration loading/saving

### Phase 4: Enhancement

8. **Add search capabilities**
   - Implement metadata-based search
   - Add filtering options
   - Create query interface

9. **Create document pairing**
   - Auto-detect and pair question papers with mark schemes
   - Implement unified JSON creation for pairs

## 6. Implementation Sequence

For each component, follow this implementation sequence:

1. Define interfaces and class signatures
2. Implement core functionality
3. Add error handling
4. Write unit tests
5. Document with docstrings
6. Create examples of usage
