# ExamContentParser Implementation Plan

## 1. Class Structure and Component Interaction

**Key Components:**

- `ExamContentParser` class: Main orchestrator for the parsing process
- `QuestionAndMarkschemeParser`: Creates prompts by combining question paper and mark scheme content
- `MistralLLMClient`: Handles communication with the Mistral AI API
- Hierarchical index: JSON structure for organizing exam data

**Class Initialization Parameters:**

- LLM client (MistralClient instance)
- Path to hierarchical index
- Base paths for source data (OCR results)
- Optional logging configuration

**Core Methods:**

- `__init__`: Initialize with necessary components and configurations
- `parse_exam_content`: Main entry point to process a specific exam paper and mark scheme pair
- `update_index`: Method to integrate parsed data into hierarchical index
- `extract_media_files`: Method to identify and process media file references

### Implementation Progress
- ✅ Implemented core class structure in exam_content_parser.py
- ✅ Added necessary imports for related modules
- ✅ Implemented `__init__` method with proper parameter validation
- ✅ Created `parse_exam_content` method framework with error handling
- ✅ Implemented `_load_exam_content_and_metadata` method
- ✅ Added method signatures for remaining core methods:
  - `_process_exam_content`
  - `_extract_media_files`
  - `_add_media_file_references`
  - `_update_index`
- ✅ Designed sliding window approach for data processing
- ⏳ Next steps: Implement sliding window content processor (Step 2)

## 2. Data Loading and Preparation

**Key Functionality:**

- Load JSON files for exam papers and mark schemes
- Extract metadata from corresponding metadata files
- Create sliding window approach for content processing
- Generate content windows for the LLM to process
- Track progress through exam content based on LLM feedback

**Implementation Details:**

- Use Python's json module to load content
- Use pathlib for cross-platform path manipulation
- Process content in windows of approximately two pages at a time
- Allow question paper and mark scheme indices to advance at different rates
- Extract content based on current indices and window size
- Create generator pattern for iterative processing

### Implementation Progress
- ✅ Designed sliding window approach for content processing
- ✅ Implemented `_process_exam_content` method with a sliding window approach in `exam_content_parser.py`
- ✅ Implemented `_create_content_window` method to prepare content for LLM processing
- ✅ Implemented `_parse_llm_response` to extract structured data from LLM responses
- ✅ Added `process_exam_from_index` method to process exams directly from hierarchical index
- ✅ Developed error handling for LLM response parsing
- ✅ Integrated with `QuestionAndMarkschemeParser` for content preparation
- ⏳ Next steps: Implement LLM-based parsing of question and mark scheme content (Step 3)

## 3. LLM-Based Content Parsing

**Processing Workflow:**

- Process exam content using the sliding window approach implemented in Step 2
- Leverage the LLM to identify questions and mark schemes within each content window
- Track progress through documents using indices returned by the LLM
- Assemble structured question and mark scheme data from multiple windows if needed

**LLM Interaction:**

- Format prompts using `QuestionAndMarkschemeParser` with content from both documents
- Request JSON-formatted responses containing:
  - Parsed questions with their text and mark scheme information
  - Next indices for question paper and mark scheme to continue processing
  - Next question number to maintain continuity
- Parse and validate LLM responses using the `_parse_llm_response` method

**Integration with Step 2:**

- Use the sliding window approach to provide the LLM with manageable content chunks
- Allow asynchronous progress through question papers and mark schemes
- Handle cases where question and mark scheme indices progress at different rates
- Collect parsed questions from all windows into a comprehensive result

### Implementation Progress
- ✅ Enhanced `_parse_llm_response` method with robust error handling for:
  - Malformed JSON responses
  - Missing required fields
  - JSON extraction from various response formats
  - Field validation and default value handling
- ✅ Added JSON repair capability using the json-repair package
- ✅ Implemented structured question validation and standardization:
  - Required fields verification (question_number, question_text, mark_scheme)
  - Optional fields with defaults (max_marks, assessment_objectives) 
  - Handling for incomplete questions that span multiple content windows
  - Smart field inference when data is missing or incomplete
- ✅ Added support for question hierarchy with parent-child relationships
  - Question/sub-question structure standardization 
  - Recursive validation for nested question structures
- ✅ Developed error recovery mechanisms:
  - Fallback strategies for ambiguous content
  - Inference of missing navigation fields
  - Support for various question numbering schemes

## 4. Media File Handling

**Media Extraction Approach:**

- Parse markdown content for image references
- Extract image IDs from OCR JSON
- Map image IDs to actual file paths in OCR directories
- Create relative paths that work within the project structure
- Associate media files with specific questions based on content proximity

**Media Dictionary Structure:**

- Keys: Image reference IDs used in markdown
- Values: Paths to image files, dimensions, and location information

**Challenges to Address:**

- Images might span multiple questions
- Some images might be decorative rather than content-related
- Need to handle various image reference formats

### Implementation Progress
- ✅ Implemented `_extract_media_files` method to extract media information from page content
- ✅ Implemented `_add_media_file_references` method to orchestrate media file handling:
  - Extracts all media files from all pages in exam content
  - Associates media with questions based on markdown image references
  - Associates media with questions based on page context (same-page association)
  - Handles sub-questions recursively
- ✅ Implemented `_associate_media_by_page` method to link media files to questions based on page indices
- ✅ Added comprehensive error handling for cases where:
  - Media references are missing or malformed
  - Questions lack page index information
  - Media path information is incomplete
- ✅ Created and verified comprehensive test suite for media handling methods
  - Unit tests for media extraction functionality
  - Tests for direct reference association
  - Tests for page-based media association
  - Tests for error handling edge cases
- ✅ Used the page-based approach as discussed, processing each page of question papers to:
  - Identify media present on the page
  - Associate that media with questions on the same page
  - Add media metadata (coordinates, path, etc.) to questions
- ✅ Ensured proper handling of image references in question text using regex pattern matching

## 5. Index Integration

**Index Structure Understanding:**

- Hierarchical organization by subject, year, qualification, and unit
- Individual exams stored under appropriate branches
- Questions will be added under appropriate unit entries

**Integration Approach:**

- Load existing hierarchical index
- Navigate to appropriate section based on metadata
- Create new entries if they don't exist
- Add or update questions array with new content
- Preserve existing structure and data
- Save updated index back to file

**Data Integration:**

- Ensure question structure matches expected format
- Add additional media_file_paths information
- Maintain any existing question data if present

### Implementation Progress
- ✅ Implemented `_update_index` method to integrate processed question data into the hierarchical index
- ✅ Added functionality to traverse the nested index structure and locate document records
- ✅ Included timestamp tracking to record when a document was processed
- ✅ Created option to write to a new file (`final_index.json`) during development
- ✅ Added comprehensive error handling for:
  - Document records not found in the index
  - Invalid input parameters
  - Index file access issues
- ✅ Implemented validation for required parameters (document_id, document_record)
- ✅ Added detailed logging for each step of the index update process
- ✅ Created comprehensive test suite for index integration:
  - Tests for successful document updates
  - Tests for document not found scenarios
  - Tests for error handling with invalid indexes
  - Tests for parameter validation
  - Tests for integrating with real hierarchical index structure
- ✅ Modified main processing flow to properly call `_update_index` after question parsing
- ✅ Added sample program to test the entire integration workflow

## 6. Error Handling and Logging

**Error Handling Strategy:**

- Implement comprehensive try-except blocks
- Log detailed error information
- Fail gracefully with meaningful error messages
- Implement recovery mechanisms where possible

**Logging Implementation:**

- Use Python's built-in logging module
- Configure different logging levels (DEBUG, INFO, ERROR)
- Log progress through key processing stages
- Include timing information for performance analysis
- Create separate log files for each processing run

**Failure Recovery:**

- Save intermediate results when processing multiple files
- Allow resuming from last successfully processed item
- Document error states for manual intervention when needed

### Implementation Progress
<!-- Progress updates for error handling and logging -->

## 7. CLI Interface

**Command Line Arguments:**

- Exam paper path
- Mark scheme path
- Output path for index
- Configuration options
- Verbosity control
- Help information

**Usage Examples:**

- Process single exam: `python -m src.ExamContentParser.exam_content_parser --question-paper path/to/paper --mark-scheme path/to/scheme`
- Process all exams: `python -m src.ExamContentParser.exam_content_parser --process-all`
- Specify output: `python -m src.ExamContentParser.exam_content_parser --output path/to/output`

**Progress Reporting:**

- Display progress bars for long-running operations
- Show current processing stage
- Provide summary statistics upon completion

### Implementation Progress
<!-- Progress updates for CLI interface -->
