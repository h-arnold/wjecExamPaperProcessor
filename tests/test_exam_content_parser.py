"""
Tests for the ExamContentParser class.

This module contains tests for the ExamContentParser class, focusing on:
1. Initialisation
2. Content loading
3. Sliding window content processing
4. LLM response parsing
"""

import os
import sys
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Add the project root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the ExamContentParser class
from src.ExamContentParser.exam_content_parser import ExamContentParser
from src.Llm_client.mistral_client import MistralLLMClient


# --- Fixtures --- #

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield Path(tmpdirname)

@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    return MagicMock(spec=MistralLLMClient)

@pytest.fixture
def temp_index_file(temp_dir):
    """Create a temporary index file."""
    index_path = temp_dir / "test_index.json"
    with open(index_path, 'w') as f:
        json.dump({"subjects": {}}, f)
    yield index_path

@pytest.fixture
def temp_metadata_dir(temp_dir):
    """Create temporary metadata directories."""
    metadata_path = temp_dir / "metadata"
    metadata_path.mkdir()
    
    # Create subdirectories
    (metadata_path / "question_papers").mkdir()
    (metadata_path / "mark_schemes").mkdir()
    
    return metadata_path

@pytest.fixture
def temp_ocr_results_dir(temp_dir):
    """Create temporary OCR results directory."""
    ocr_path = temp_dir / "ocr_results"
    ocr_path.mkdir()
    return ocr_path

@pytest.fixture
def mock_question_paper_content():
    """Create mock question paper content."""
    return [
        {
            "index": 0,
            "markdown": "# GCE AS/A Level\n\n## WJEC\n\n## COMPUTER SCIENCE - Unit 1\n\nExam Title\nA.M. TUESDAY, 18 June 2023\n\n2 hours",
            "images": [],
            "dimensions": {"width": 1654, "height": 2339}
        },
        {
            "index": 1,
            "markdown": "Answer all questions.\n\n1. Explain the role of the control unit in a CPU.\n\n2. Compare and contrast the Von Neumann and Harvard architectures.",
            "images": [],
            "dimensions": {"width": 1654, "height": 2339}
        },
        {
            "index": 2,
            "markdown": "3. Describe how floating point numbers are represented in binary.\n\n4. Explain the concept of virtual memory.",
            "images": [],
            "dimensions": {"width": 1654, "height": 2339}
        }
    ]

@pytest.fixture
def mock_mark_scheme_content():
    """Create mock mark scheme content."""
    return [
        {
            "index": 0,
            "markdown": "# GCE AS/A Level\n\n## WJEC\n\n## COMPUTER SCIENCE - Unit 1\n\nMark Scheme\nA.M. TUESDAY, 18 June 2023",
            "images": [],
            "dimensions": {"width": 1654, "height": 2339}
        },
        {
            "index": 1,
            "markdown": "# Mark Scheme\n\n| Question | Answer | Marks |\n| :--: | :-- | :--: |\n| 1 | The control unit: | |\n| | • Fetches, decodes and executes instructions | 1 |\n| | • Controls the flow of data within the CPU | 1 |\n| | • Generates control signals for internal/external components | 1 |\n| | • Controls the timing of operations using the system clock | 1 |",
            "images": [],
            "dimensions": {"width": 1654, "height": 2339}
        },
        {
            "index": 2,
            "markdown": "| Question | Answer | Marks |\n| :--: | :-- | :--: |\n| 2 | Von Neumann architecture: | |\n| | • Uses a single memory space for both instructions and data | 1 |\n| | Cannot fetch instructions and data simultaneously | 1 |\n| | Harvard architecture: | |\n| | • Separate memory spaces for instructions and data | 1 |\n| | Can fetch instructions and data simultaneously | 1 |\n| | Typically faster but more complex to implement | 1 |",
            "images": [],
            "dimensions": {"width": 1654, "height": 2339}
        }
    ]

@pytest.fixture
def mock_question_paper_metadata():
    """Create mock question paper metadata."""
    return {
        "Type": "Question Paper",
        "Year": 2023,
        "Qualification": "AS Level",
        "Subject": "Computer Science",
        "Exam Paper": "Unit 1: Fundamentals of Computer Science",
        "Exam Season": "Summer",
        "QuestionStartIndex": 1,
        "FilePath": "ocr_results/test_qp.json"
    }

@pytest.fixture
def mock_mark_scheme_metadata():
    """Create mock mark scheme metadata."""
    return {
        "Type": "Mark Scheme",
        "Year": 2023,
        "Qualification": "AS Level",
        "Subject": "Computer Science",
        "Exam Paper": "Unit 1: Fundamentals of Computer Science",
        "Exam Season": "Summer",
        "MarkSchemeStartIndex": 1,
        "FilePath": "ocr_results/test_ms.json"
    }

# --- Tests --- #

class TestExamContentParserInit:
    """Test ExamContentParser initialization."""
    
    def test_init_with_valid_params(self, mock_llm_client, temp_index_file, temp_ocr_results_dir, temp_metadata_dir):
        """Test initialization with valid parameters."""
        parser = ExamContentParser(
            llm_client=mock_llm_client,
            index_path=temp_index_file,
            ocr_results_path=temp_ocr_results_dir,
            metadata_path=temp_metadata_dir
        )
        
        assert parser.llm_client == mock_llm_client
        assert parser.index_path == temp_index_file
        assert parser.ocr_results_path == temp_ocr_results_dir
        assert parser.metadata_path == temp_metadata_dir
    
    def test_init_with_nonexistent_paths(self, mock_llm_client, temp_dir):
        """Test initialization with non-existent paths."""
        with pytest.raises(FileNotFoundError):
            ExamContentParser(
                llm_client=mock_llm_client,
                index_path=temp_dir / "nonexistent.json",
                ocr_results_path=temp_dir / "ocr_results",
                metadata_path=temp_dir / "metadata"
            )


class TestExamContentLoading:
    """Test exam content loading functionality."""

    @patch("builtins.open", new_callable=mock_open)
    def test_load_exam_content_and_metadata(self, mock_file, mock_llm_client, temp_index_file, 
                                          temp_ocr_results_dir, temp_metadata_dir,
                                          mock_question_paper_content, mock_question_paper_metadata):
        """Test loading exam content and metadata."""
        # Setup mock files
        mock_file.side_effect = [
            mock_open(read_data=json.dumps(mock_question_paper_metadata)).return_value,
            mock_open(read_data=json.dumps(mock_question_paper_content)).return_value
        ]
        
        parser = ExamContentParser(
            llm_client=mock_llm_client,
            index_path=temp_index_file,
            ocr_results_path=temp_ocr_results_dir,
            metadata_path=temp_metadata_dir
        )
        
        # Test the method
        content, metadata = parser._load_exam_content_and_metadata("test_qp", "question_papers")
        
        # Verify results
        assert content == mock_question_paper_content
        assert metadata == mock_question_paper_metadata
        
    def test_load_exam_content_and_metadata_file_not_found(self, mock_llm_client, temp_index_file, 
                                                         temp_ocr_results_dir, temp_metadata_dir):
        """Test handling of FileNotFoundError when loading exam content."""
        parser = ExamContentParser(
            llm_client=mock_llm_client,
            index_path=temp_index_file,
            ocr_results_path=temp_ocr_results_dir,
            metadata_path=temp_metadata_dir
        )
        
        # Test with non-existent file
        with pytest.raises(FileNotFoundError):
            parser._load_exam_content_and_metadata("nonexistent", "question_papers")


class TestContentWindows:
    """Test content window creation functionality."""
    
    def test_create_content_window(self, mock_llm_client, temp_index_file, temp_ocr_results_dir, 
                                 temp_metadata_dir, mock_question_paper_content, mock_mark_scheme_content):
        """Test creating content windows for processing."""
        parser = ExamContentParser(
            llm_client=mock_llm_client,
            index_path=temp_index_file,
            ocr_results_path=temp_ocr_results_dir,
            metadata_path=temp_metadata_dir
        )
        
        # Test window creation
        window = parser._create_content_window(
            mock_question_paper_content,
            mock_mark_scheme_content,
            qp_current_index=1,
            ms_current_index=1,
            current_question=1
        )
        
        # Verify window structure
        assert window["question_paper_content"] == mock_question_paper_content
        assert window["mark_scheme_content"] == mock_mark_scheme_content
        assert window["question_start_index"] == 1
        assert window["mark_scheme_start_index"] == 1
        assert window["current_question_number"] == 1
        assert window["current_question_paper_index"] == 1
        assert window["current_mark_scheme_index"] == 1


class TestLLMResponseParsing:
    """Test LLM response parsing functionality."""
    
    def test_parse_llm_response_json_block(self, mock_llm_client, temp_index_file, 
                                         temp_ocr_results_dir, temp_metadata_dir):
        """Test parsing LLM response with a JSON code block."""
        parser = ExamContentParser(
            llm_client=mock_llm_client,
            index_path=temp_index_file,
            ocr_results_path=temp_ocr_results_dir,
            metadata_path=temp_metadata_dir
        )
        
        # Mock response with JSON code block
        response = """
        I've analyzed the content and extracted the questions.
        
        ```json
        {
            "questions": [
                {
                    "question_number": 1,
                    "question_text": "Explain the role of the control unit in a CPU.",
                    "mark_scheme": "The control unit fetches, decodes and executes instructions, controls data flow, generates control signals, and controls timing operations.",
                    "marks": 4
                }
            ],
            "next_question_paper_index": 2,
            "next_mark_scheme_index": 2,
            "next_question_number": 2
        }
        ```
        
        Let me know if you need anything else!
        """
        
        # Parse response
        result = parser._parse_llm_response(response)
        
        # Verify parsed data
        assert "questions" in result
        assert len(result["questions"]) == 1
        assert result["questions"][0]["question_number"] == 1
        assert "next_question_paper_index" in result
        assert result["next_question_paper_index"] == 2
        assert "next_mark_scheme_index" in result
        assert result["next_mark_scheme_index"] == 2
        assert "next_question_number" in result
        assert result["next_question_number"] == 2
    
    def test_parse_llm_response_direct_json(self, mock_llm_client, temp_index_file, 
                                          temp_ocr_results_dir, temp_metadata_dir):
        """Test parsing LLM response with direct JSON (no code block)."""
        parser = ExamContentParser(
            llm_client=mock_llm_client,
            index_path=temp_index_file,
            ocr_results_path=temp_ocr_results_dir,
            metadata_path=temp_metadata_dir
        )
        
        # Mock response with direct JSON
        response = """{"questions": [{"question_number": 1, "question_text": "Explain the role of the control unit in a CPU.", "mark_scheme": "The control unit fetches, decodes and executes instructions.", "marks": 4}], "next_question_paper_index": 2, "next_mark_scheme_index": 2, "next_question_number": 2}"""
        
        # Parse response
        result = parser._parse_llm_response(response)
        
        # Verify parsed data
        assert "questions" in result
        assert len(result["questions"]) == 1
        assert result["questions"][0]["question_number"] == 1
        assert "next_question_paper_index" in result
        assert result["next_question_paper_index"] == 2
    
    def test_parse_llm_response_missing_fields(self, mock_llm_client, temp_index_file, 
                                             temp_ocr_results_dir, temp_metadata_dir):
        """Test parsing LLM response with missing required fields."""
        parser = ExamContentParser(
            llm_client=mock_llm_client,
            index_path=temp_index_file,
            ocr_results_path=temp_ocr_results_dir,
            metadata_path=temp_metadata_dir
        )
        
        # Mock response missing critical fields
        response = """
        ```json
        {
            "questions": [
                {
                    "question_number": 1,
                    "question_text": "Explain the role of the control unit in a CPU."
                }
            ]
        }
        ```
        """
        
        # Parsing should raise ValueError due to missing next_* fields
        with pytest.raises(ValueError):
            parser._parse_llm_response(response)
    
    def test_parse_llm_response_invalid_json(self, mock_llm_client, temp_index_file, 
                                           temp_ocr_results_dir, temp_metadata_dir):
        """Test parsing LLM response with invalid JSON."""
        parser = ExamContentParser(
            llm_client=mock_llm_client,
            index_path=temp_index_file,
            ocr_results_path=temp_ocr_results_dir,
            metadata_path=temp_metadata_dir
        )
        
        # Mock response with invalid JSON
        response = """
        ```json
        {
            "questions": [
                {
                    "question_number": 1,
                    "question_text": "Explain the role of the control unit in a CPU.",
                    "mark_scheme": "The control unit controls the CPU"
                },
            ],
            "next_question_paper_index": 2,
        }
        ```
        """
        
        # Parsing should raise ValueError due to invalid JSON
        with pytest.raises(ValueError):
            parser._parse_llm_response(response)


class TestProcessExamContent:
    """Test process_exam_content functionality."""
    
    @patch.object(MistralLLMClient, "generate_json")
    def test_process_exam_content(self, mock_generate, mock_llm_client, temp_index_file, 
                                temp_ocr_results_dir, temp_metadata_dir, 
                                mock_question_paper_content, mock_mark_scheme_content,
                                mock_question_paper_metadata, mock_mark_scheme_metadata):
        """Test processing exam content with mocked LLM responses."""
        # Set up parser
        parser = ExamContentParser(
            llm_client=mock_llm_client,
            index_path=temp_index_file,
            ocr_results_path=temp_ocr_results_dir,
            metadata_path=temp_metadata_dir
        )
        
        # Set up mock responses from LLM
        mock_llm_responses = [
            # First response: Questions 1 with navigation to question 2
            """
            ```json
            {
                "questions": [
                    {
                        "question_number": 1,
                        "question_text": "Explain the role of the control unit in a CPU.",
                        "mark_scheme": "The control unit fetches, decodes and executes instructions, controls data flow, generates control signals, and controls timing operations.",
                        "marks": 4
                    }
                ],
                "next_question_paper_index": 1,
                "next_mark_scheme_index": 2,
                "next_question_number": 2
            }
            ```
            """,
            # Second response: Questions 2 with end of processing
            """
            ```json
            {
                "questions": [
                    {
                        "question_number": 2,
                        "question_text": "Compare and contrast the Von Neumann and Harvard architectures.",
                        "mark_scheme": "Von Neumann: shared memory for instructions and data. Harvard: separate memory spaces for instructions and data, allowing simultaneous fetching.",
                        "marks": 5
                    }
                ],
                "next_question_paper_index": 2,
                "next_mark_scheme_index": 3,
                "next_question_number": 3
            }
            ```
            """
        ]
        
        # Configure the mock to return different values on each call
        mock_generate.side_effect = mock_llm_responses
        parser.llm_client.generate_json = mock_generate
        
        # Process the exam content
        parsed_questions = parser._process_exam_content(
            mock_question_paper_content,
            mock_question_paper_metadata,
            mock_mark_scheme_content,
            mock_mark_scheme_metadata
        )
        
        # Verify number of calls to the LLM
        assert mock_generate.call_count == 2
        
        # Verify parsed questions
        assert len(parsed_questions) == 2
        assert parsed_questions[0]["question_number"] == 1
        assert parsed_questions[1]["question_number"] == 2
        assert "Explain the role of the control unit" in parsed_questions[0]["question_text"]
        assert "Von Neumann and Harvard architectures" in parsed_questions[1]["question_text"]
    
    @patch.object(MistralLLMClient, "generate_json")
    def test_process_exam_content_error_handling(self, mock_generate, mock_llm_client, 
                                              temp_index_file, temp_ocr_results_dir, 
                                              temp_metadata_dir, mock_question_paper_content,
                                              mock_mark_scheme_content, mock_question_paper_metadata,
                                              mock_mark_scheme_metadata):
        """Test error handling in process_exam_content."""
        # Set up parser
        parser = ExamContentParser(
            llm_client=mock_llm_client,
            index_path=temp_index_file,
            ocr_results_path=temp_ocr_results_dir,
            metadata_path=temp_metadata_dir
        )
        
        # Make the LLM client raise an exception
        mock_generate.side_effect = Exception("API error")
        parser.llm_client.generate_json = mock_generate
        
        # Process the exam content - should handle the exception gracefully
        parsed_questions = parser._process_exam_content(
            mock_question_paper_content,
            mock_question_paper_metadata,
            mock_mark_scheme_content,
            mock_mark_scheme_metadata
        )
        
        # Verify the result is an empty list due to the error
        assert len(parsed_questions) == 0


class TestIndexIntegration:
    """Test integration with hierarchical index."""
    
    def test_process_exam_from_index(self, mock_llm_client, temp_index_file, 
                                   temp_ocr_results_dir, temp_metadata_dir):
        """Test processing exams directly from hierarchical index."""
        # Create a parser
        parser = ExamContentParser(
            llm_client=mock_llm_client,
            index_path=temp_index_file,
            ocr_results_path=temp_ocr_results_dir,
        )
        
        # Create a mock exam entry from a hierarchical index
        mock_exam_entry = {
            "documents": {
                "Question Paper": [
                    {
                        "id": "test_qp",
                        "content_path": str(temp_ocr_results_dir / "test_qp.json"),
                        "metadata_path": str(temp_metadata_dir / "question_papers" / "test_qp-metadata.json")
                    }
                ],
                "Mark Scheme": [
                    {
                        "id": "test_ms",
                        "content_path": str(temp_ocr_results_dir / "test_ms.json"),
                        "metadata_path": str(temp_metadata_dir / "mark_schemes" / "test_ms-metadata.json")
                    }
                ]
            }
        }
        
        # Mock the parse_exam_content method to avoid actual processing
        with patch.object(parser, 'parse_exam_content', return_value=True) as mock_parse:
            # Call the method
            result = parser.process_exam_from_index(mock_exam_entry)
            
            # Verify the method called parse_exam_content with the correct IDs
            mock_parse.assert_called_once_with('test_qp', 'test_ms')
            assert result is True
    
    def test_process_exam_from_index_missing_documents(self, mock_llm_client, temp_index_file, 
                                                   temp_ocr_results_dir):
        """Test process_exam_from_index error handling with missing documents."""
        # Create a parser
        parser = ExamContentParser(
            llm_client=mock_llm_client,
            index_path=temp_index_file,
            ocr_results_path=temp_ocr_results_dir
        )
        
        # Create invalid exam entries
        missing_documents = {}
        missing_qp = {"documents": {"Mark Scheme": [{"id": "test_ms"}]}}
        missing_ms = {"documents": {"Question Paper": [{"id": "test_qp"}]}}
        
        # Test with missing documents section
        with pytest.raises(ValueError, match="does not contain documents section"):
            parser.process_exam_from_index(missing_documents)
        
        # Test with missing Question Paper
        with pytest.raises(ValueError, match="No Question Paper found"):
            parser.process_exam_from_index(missing_qp)
        
        # Test with missing Mark Scheme
        with pytest.raises(ValueError, match="No Mark Scheme found"):
            parser.process_exam_from_index(missing_ms)
            
    def test_update_index(self, mock_llm_client, temp_dir):
        """Test updating the hierarchical index with processed question data."""
        # Create a mock index file with a structured hierarchical index
        index_content = {
            "subjects": {
                "Computer Science": {
                    "years": {
                        "2023": {
                            "qualifications": {
                                "A-Level": {
                                    "exams": {
                                        "Unit 1": {
                                            "documents": {
                                                "Question Paper": [
                                                    {
                                                        "id": "test_doc_id",
                                                        "content_path": "ocr_results/test_doc.json"
                                                    }
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
        
        # Write mock index to file
        index_path = temp_dir / "test_index.json"
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index_content, f)
        
        # Create test parsed questions
        parsed_questions = [
            {
                "question_number": "1",
                "question_text": "Test question 1",
                "mark_scheme": "Test mark scheme 1",
                "max_marks": 5
            },
            {
                "question_number": "2",
                "question_text": "Test question 2",
                "mark_scheme": "Test mark scheme 2",
                "max_marks": 10
            }
        ]
        
        # Create metadata
        metadata = {"QuestionStartIndex": 1}
        
        # Create the parser
        parser = ExamContentParser(
            llm_client=mock_llm_client,
            index_path=index_path,
            ocr_results_path=temp_dir
        )
        
        # Update the index with the mock document and questions
        document_record = {"id": "test_doc_id", "content_path": "ocr_results/test_doc.json"}
        parser._update_index(parsed_questions, metadata, "test_doc_id", document_record)
        
        # Verify the output file was created
        output_path = temp_dir / "final_index.json"
        assert output_path.exists()
        
        # Load and verify the updated index
        with open(output_path, 'r', encoding='utf-8') as f:
            updated_index = json.load(f)
        
        # Check that the questions were added to the document record
        doc_record = updated_index["subjects"]["Computer Science"]["years"]["2023"]["qualifications"]["A-Level"]["exams"]["Unit 1"]["documents"]["Question Paper"][0]
        assert "questions" in doc_record
        assert len(doc_record["questions"]) == 2
        assert doc_record["questions"][0]["question_number"] == "1"
        assert doc_record["questions"][1]["question_number"] == "2"
        assert "processed_at" in doc_record
        
    def test_update_index_document_not_found(self, mock_llm_client, temp_dir):
        """Test handling of document not found during index update."""
        # Create a mock index file
        index_content = {
            "subjects": {
                "Computer Science": {
                    "years": {
                        "2023": {
                            "qualifications": {
                                "A-Level": {
                                    "exams": {
                                        "Unit 1": {
                                            "documents": {
                                                "Question Paper": [
                                                    {
                                                        "id": "existing_doc",
                                                        "content_path": "ocr_results/existing_doc.json"
                                                    }
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
        
        # Write mock index to file
        index_path = temp_dir / "test_index.json"
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index_content, f)
        
        # Create the parser
        parser = ExamContentParser(
            llm_client=mock_llm_client,
            index_path=index_path,
            ocr_results_path=temp_dir
        )
        
        # Mock parsed questions and metadata
        parsed_questions = [{"question_number": "1", "question_text": "Test"}]
        metadata = {}
        
        # Try to update with non-existent document ID
        with patch("logging.Logger.warning") as mock_warning:
            parser._update_index(parsed_questions, metadata, "nonexistent_doc_id", {"id": "nonexistent_doc_id"})
            mock_warning.assert_called_with("Could not find document record for nonexistent_doc_id in the index")
            
        # Verify the output file still exists (but was not updated with our document)
        output_path = temp_dir / "final_index.json"
        assert output_path.exists()
        
    def test_update_index_error_handling(self, mock_llm_client, temp_dir):
        """Test error handling during index update."""
        # Create a mock index file
        index_path = temp_dir / "test_index.json"
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write("{invalid json")  # Deliberately write invalid JSON
        
        # Create the parser
        parser = ExamContentParser(
            llm_client=mock_llm_client,
            index_path=index_path,
            ocr_results_path=temp_dir
        )
        
        # Mock parsed questions and metadata
        parsed_questions = [{"question_number": "1", "question_text": "Test"}]
        metadata = {}
        
        # Try to update with invalid index file
        with pytest.raises(Exception):
            parser._update_index(parsed_questions, metadata, "test_id", {"id": "test_id"})
            
    def test_update_index_validation(self, mock_llm_client, temp_dir):
        """Test validation of input parameters in _update_index."""
        # Create a basic index file
        index_path = temp_dir / "test_index.json"
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump({"subjects": {}}, f)
        
        # Create the parser
        parser = ExamContentParser(
            llm_client=mock_llm_client,
            index_path=index_path,
            ocr_results_path=temp_dir
        )
        
        # Test with missing document_id
        with pytest.raises(ValueError, match="Document ID and document record are required"):
            parser._update_index([], {}, document_id=None, document_record={"id": "something"})
            
        # Test with missing document_record
        with pytest.raises(ValueError, match="Document ID and document record are required"):
            parser._update_index([], {}, document_id="test_id", document_record=None)


class TestMediaFileHandling:
    """Test media file extraction and handling functionality."""
    
    def test_extract_media_files(self, mock_llm_client, temp_index_file, 
                               temp_ocr_results_dir):
        """Test extracting media files from page content."""
        # Create parser instance
        parser = ExamContentParser(
            llm_client=mock_llm_client,
            index_path=temp_index_file,
            ocr_results_path=temp_ocr_results_dir
        )
        
        # Create page content with images
        page_content = {
            "index": 1,
            "markdown": "# Test page with images\n\n![img-0.jpeg](img-0.jpeg)\nThis is a test page.\n\n![img-1.jpeg](img-1.jpeg)",
            "images": [
                {
                    "id": "img-0.jpeg",
                    "top_left_x": 100,
                    "top_left_y": 100,
                    "bottom_right_x": 300,
                    "bottom_right_y": 300,
                    "image_path": "test_paper/images/img_1_0.jpeg"
                },
                {
                    "id": "img-1.jpeg",
                    "top_left_x": 400,
                    "top_left_y": 400,
                    "bottom_right_x": 600,
                    "bottom_right_y": 600,
                    "image_path": "test_paper/images/img_1_1.jpeg"
                }
            ]
        }
        
        # Extract media files
        media_files = parser._extract_media_files(page_content)
        
        # Verify the extraction
        assert len(media_files) == 2
        assert "img-0.jpeg" in media_files
        assert "img-1.jpeg" in media_files
        
        # Check first image properties
        assert media_files["img-0.jpeg"]["path"] == "test_paper/images/img_1_0.jpeg"
        assert media_files["img-0.jpeg"]["coordinates"]["top_left_x"] == 100
        assert media_files["img-0.jpeg"]["coordinates"]["bottom_right_y"] == 300
        assert media_files["img-0.jpeg"]["page_index"] == 1
        
        # Check second image properties
        assert media_files["img-1.jpeg"]["path"] == "test_paper/images/img_1_1.jpeg"
    
    def test_extract_media_files_no_images(self, mock_llm_client, temp_index_file, 
                                         temp_ocr_results_dir):
        """Test extracting media files from a page with no images."""
        parser = ExamContentParser(
            llm_client=mock_llm_client,
            index_path=temp_index_file,
            ocr_results_path=temp_ocr_results_dir
        )
        
        # Create page content with no images
        page_content = {
            "index": 1,
            "markdown": "# Test page with no images\n\nThis is a test page.",
            "images": []
        }
        
        # Extract media files
        media_files = parser._extract_media_files(page_content)
        
        # Verify the extraction - should be empty
        assert isinstance(media_files, dict)
        assert len(media_files) == 0
    
    def test_add_media_file_references(self, mock_llm_client, temp_index_file,
                                     temp_ocr_results_dir):
        """Test adding media file references to questions."""
        parser = ExamContentParser(
            llm_client=mock_llm_client,
            index_path=temp_index_file,
            ocr_results_path=temp_ocr_results_dir
        )
        
        # Create parsed questions with image references
        parsed_questions = [
            {
                "question_number": "1",
                "question_text": "Explain the diagram ![img-0.jpeg](img-0.jpeg) and its components.",
                "mark_scheme": "Components correctly identified (1 mark)",
                "max_marks": 5,
                "page_index": 1
            },
            {
                "question_number": "2",
                "question_text": "Analyze the structure shown in the second image ![img-1.jpeg](img-1.jpeg)",
                "mark_scheme": "Structure analysis correct (2 marks)",
                "max_marks": 10,
                "page_index": 1,
                "sub_questions": [
                    {
                        "question_number": "2.1",
                        "question_text": "Identify part A in the diagram ![img-1.jpeg](img-1.jpeg)",
                        "mark_scheme": "Part A identified correctly (1 mark)",
                        "max_marks": 2,
                        "page_index": 1
                    }
                ]
            },
            {
                "question_number": "3",
                "question_text": "This question has no image references",
                "mark_scheme": "Answer should be textual (2 marks)",
                "max_marks": 5,
                "page_index": 2
            }
        ]
        
        # Create content with images
        content = [
            {
                "index": 0,
                "markdown": "# Test Paper",
                "images": []
            },
            {
                "index": 1,
                "markdown": "# Questions with Images\n\n1. Explain the diagram ![img-0.jpeg](img-0.jpeg) and its components.\n\n2. Analyze the structure shown in the second image ![img-1.jpeg](img-1.jpeg)",
                "images": [
                    {
                        "id": "img-0.jpeg",
                        "top_left_x": 100,
                        "top_left_y": 100,
                        "bottom_right_x": 300,
                        "bottom_right_y": 300,
                        "image_path": "test_paper/images/img_1_0.jpeg"
                    },
                    {
                        "id": "img-1.jpeg",
                        "top_left_x": 400,
                        "top_left_y": 400,
                        "bottom_right_x": 600,
                        "bottom_right_y": 600,
                        "image_path": "test_paper/images/img_1_1.jpeg"
                    }
                ]
            },
            {
                "index": 2,
                "markdown": "3. This question has no image references",
                "images": []
            }
        ]
        
        # Add media file references
        parser._add_media_file_references(parsed_questions, content)
        
        # Verify question 1 has the correct media files
        assert "media_files" in parsed_questions[0]
        assert len(parsed_questions[0]["media_files"]) == 2  # Both images on page 1
        # Verify one of the images is img-0.jpeg
        assert any(m["id"] == "img-0.jpeg" for m in parsed_questions[0]["media_files"])
        # Verify the other image is img-1.jpeg
        assert any(m["id"] == "img-1.jpeg" for m in parsed_questions[0]["media_files"])
        
        # Verify question 2 has both media files from page 1
        assert "media_files" in parsed_questions[1]
        assert len(parsed_questions[1]["media_files"]) == 2
        assert any(m["id"] == "img-0.jpeg" for m in parsed_questions[1]["media_files"])
        assert any(m["id"] == "img-1.jpeg" for m in parsed_questions[1]["media_files"])
        
        # Verify sub-question 2.1 has both media files from page 1
        assert "media_files" in parsed_questions[1]["sub_questions"][0]
        assert len(parsed_questions[1]["sub_questions"][0]["media_files"]) == 2
        assert any(m["id"] == "img-0.jpeg" for m in parsed_questions[1]["sub_questions"][0]["media_files"])
        assert any(m["id"] == "img-1.jpeg" for m in parsed_questions[1]["sub_questions"][0]["media_files"])
        
        # Verify question 3 doesn't have media files
        assert "media_files" in parsed_questions[2]
        assert len(parsed_questions[2]["media_files"]) == 0