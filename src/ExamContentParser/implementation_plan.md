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
<!-- Progress updates for class structure implementation -->

## 2. Data Loading and Preparation

**Key Functionality:**

- Load JSON files for exam papers and mark schemes
- Extract metadata from corresponding metadata files
- Determine question boundaries using metadata indices
- Group related question paper and mark scheme content
- Validate content structure before processing

**Implementation Details:**

- Use Python's json module to load content
- Use pathlib for cross-platform path manipulation
- Process files incrementally to manage memory usage
- Extract unit number, qualification, and year from metadata
- Create maps of question content to mark scheme content

### Implementation Progress
<!-- Progress updates for data loading functionality -->

## 3. Processing Pipeline

**Processing Workflow:**

- Create batches of question and mark scheme content
- Generate prompts for each batch using QuestionAndMarkschemeParser
- Submit prompts to MistralLLMClient
- Parse structured responses into question objects
- Extract and add media file references
- Update index with processed questions

**Batching Strategy:**

- Process one question at a time when possible
- For complex questions, may need to include context from adjacent content
- Use question numbers and section headers to determine logical splits

**LLM Interaction:**

- Format prompts according to LLM requirements
- Request JSON-formatted responses for consistent parsing
- Handle retry logic for API failures
- Implement backoff strategy for rate limits

### Implementation Progress
<!-- Progress updates for processing pipeline implementation -->

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
<!-- Progress updates for media file handling -->

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
<!-- Progress updates for index integration -->

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
