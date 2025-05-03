#!/usr/bin/env python3
"""
Tests for the DocumentProcessor class with MongoDB integration.

This module contains unit tests for the DocumentProcessor MongoDB integration,
covering functionality such as initializing with a DBManager, processing
documents with MongoDB storage, batch processing, and duplicate detection.
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# Add project root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.MetadataExtraction.document_processor import DocumentProcessor
from src.DBManager.db_manager import DBManager
from src.Llm_client.base_client import LLMClient
from src.FileManager.file_manager import FileManager
from src.MetadataExtraction.metadata_extractor import MetadataExtractor


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    mock_client = MagicMock(spec=LLMClient)
    
    # Configure generate_json to return a sample metadata structure
    mock_client.generate_json.return_value = {
        "Type": "Question Paper",
        "Subject": "Computer Science",
        "Qualification": "A2-Level",
        "Year": 2023,
        "Exam Season": "Summer",
        "Exam Paper": "Unit 3: Programming and System Development",
        "Exam Board": "WJEC"
    }
    
    return mock_client


@pytest.fixture
def mock_file_manager():
    """Mock file manager for testing."""
    mock_manager = MagicMock(spec=FileManager)
    
    # Configure extract_document_id to return a consistent ID
    mock_manager.extract_document_id.return_value = "test-doc-id"
    
    # Configure read_ocr_file to return some dummy content
    mock_manager.read_ocr_file.return_value = [{"page_number": 1, "text": "Sample OCR content"}]
    
    return mock_manager


@pytest.fixture
def mock_db_manager():
    """Mock DBManager for testing."""
    mock_manager = MagicMock(spec=DBManager)
    
    # Configure document_exists to return False by default (document doesn't exist)
    mock_manager.document_exists.return_value = False
    
    # Configure save_exam_metadata to return the document ID
    mock_manager.save_exam_metadata.return_value = "test-doc-id"
    
    # Configure bulk_save_exam_metadata to return a list of document IDs
    mock_manager.bulk_save_exam_metadata.return_value = ["test-doc-id-1", "test-doc-id-2"]
    
    return mock_manager


@pytest.fixture
def setup_document_processor(mock_llm_client, mock_file_manager, mock_db_manager):
    """Set up DocumentProcessor with mock dependencies."""
    processor = DocumentProcessor(
        llm_client=mock_llm_client,
        file_manager=mock_file_manager,
        db_manager=mock_db_manager
    )
    
    # Mock the MetadataExtractor methods
    mock_extractor = MagicMock(spec=MetadataExtractor)
    mock_extractor.extract_metadata.return_value = {
        "Type": "Question Paper",
        "Subject": "Computer Science",
        "Qualification": "A2-Level",
        "Year": 2023,
        "Exam Season": "Summer",
        "Exam Paper": "Unit 3: Programming and System Development",
        "Exam Board": "WJEC"
    }
    mock_extractor.identify_question_start_index.return_value = 5
    mock_extractor.enrich_metadata.return_value = {
        "Type": "Question Paper",
        "Subject": "Computer Science",
        "Qualification": "A2-Level",
        "Year": 2023,
        "Exam Season": "Summer",
        "Exam Paper": "Unit 3: Programming and System Development",
        "Exam Board": "WJEC",
        "QuestionStartIndex": 5,
        "FilePath": "mock/path/test-doc-id.json"
    }
    
    processor.metadata_extractor = mock_extractor
    
    return processor


class TestDocumentProcessorInitialization:
    """Test initialization of DocumentProcessor with DBManager."""
    
    def test_init_with_db_manager(self, mock_llm_client, mock_db_manager):
        """Test initialization with a DBManager instance."""
        processor = DocumentProcessor(
            llm_client=mock_llm_client,
            db_manager=mock_db_manager
        )
        
        # Verify DBManager is properly set
        assert processor.db_manager == mock_db_manager
    
    def test_init_with_mongodb_config(self, mock_llm_client):
        """Test initialization with MongoDB configuration parameters."""
        mongodb_config = {
            "connection_string": "mongodb://test",
            "database_name": "test-db",
            "timeout_ms": 5000
        }
        
        # Patch DBManager class to monitor its construction
        with patch('src.MetadataExtraction.document_processor.DBManager') as mock_db_manager_class:
            # Create processor with MongoDB config
            processor = DocumentProcessor(
                llm_client=mock_llm_client,
                db_manager=None,  # Set to None so it will create a new one
                mongodb_config=mongodb_config
            )
            
            # Verify DBManager was constructed with the correct parameters
            mock_db_manager_class.assert_called_once()
            
            # Extract the call arguments
            args, kwargs = mock_db_manager_class.call_args
            
            # Verify the correct config was passed
            assert kwargs.get('connection_string') == mongodb_config['connection_string']
            assert kwargs.get('database_name') == mongodb_config['database_name']
            assert kwargs.get('timeout_ms') == mongodb_config['timeout_ms']
    
    def test_init_without_db_manager_raises_error(self, mock_llm_client):
        """Test that initialization without a DBManager raises an error."""
        with pytest.raises(ValueError, match="DBManager is required"):
            DocumentProcessor(
                llm_client=mock_llm_client,
                db_manager=None,
                mongodb_config=None  # No MongoDB config either
            )


class TestProcessDocument:
    """Test processing individual documents with MongoDB integration."""
    
    def test_process_document_mongodb_storage(self, setup_document_processor):
        """Test processing a document with MongoDB storage."""
        processor = setup_document_processor
        
        # Process document with MongoDB storage
        result = processor.process_document(
            ocr_file_path="mock/path/test-doc-id.json"
        )
        
        # Verify document was checked for existence
        processor.db_manager.document_exists.assert_called_once_with("test-doc-id")
        
        # Verify metadata was extracted
        processor.metadata_extractor.extract_metadata.assert_called_once()
        
        # Verify metadata was saved to MongoDB
        processor.db_manager.save_exam_metadata.assert_called_once()
        
        # Verify result contains expected fields
        assert result["document_id"] == "test-doc-id"
        assert "metadata" in result
        assert "mongodb_id" in result
    
    def test_process_document_existing_in_mongodb(self, setup_document_processor):
        """Test processing a document that already exists in MongoDB."""
        processor = setup_document_processor
        
        # Configure document_exists to return True
        processor.db_manager.document_exists.return_value = True
        
        # Mock get_exam_metadata to return a document
        existing_metadata = {
            "examId": "test-doc-id",
            "subject": "Computer Science",
            "qualification": "A2-Level",
            "year": 2023,
            "season": "Summer",
            "unit": "Unit 3"
        }
        processor.db_manager.get_exam_metadata.return_value = existing_metadata
        
        # Process document
        result = processor.process_document(
            ocr_file_path="mock/path/test-doc-id.json"
        )
        
        # Verify document was checked for existence
        processor.db_manager.document_exists.assert_called_once_with("test-doc-id")
        
        # Verify existing document was retrieved
        processor.db_manager.get_exam_metadata.assert_called_once_with("test-doc-id")
        
        # Verify metadata was not extracted (document already exists)
        processor.metadata_extractor.extract_metadata.assert_not_called()
        
        # Verify result contains expected fields
        assert result["document_id"] == "test-doc-id"
        assert result["metadata"] == existing_metadata
        assert result["source"] == "mongodb"
        assert result["status"] == "existing"


class TestProcessDirectory:
    """Test processing directories with MongoDB integration."""
    
    def test_process_directory_batch_processing(self, setup_document_processor):
        """Test directory processing with batch processing."""
        processor = setup_document_processor
        
        # Mock glob to return a list of file paths
        test_files = [Path("mock/path/file1.json"), Path("mock/path/file2.json")]
        with patch('pathlib.Path.glob', return_value=test_files):
            # Mock _process_directory_with_mongodb
            with patch.object(processor, '_process_directory_with_mongodb') as mock_process_with_mongo:
                mock_process_with_mongo.return_value = [
                    {"document_id": "file1", "status": "new"},
                    {"document_id": "file2", "status": "existing"}
                ]
                
                # Process directory
                results = processor.process_directory(
                    directory_path="mock/path",
                    pattern="*.json"
                )
                
                # Verify _process_directory_with_mongodb was called with correct parameters
                mock_process_with_mongo.assert_called_once_with(
                    test_files, 20
                )
                
                # Verify results were returned from _process_directory_with_mongodb
                assert len(results) == 2
                assert results[0]["document_id"] == "file1"
                assert results[1]["document_id"] == "file2"
    
    def test_process_directory_empty(self, setup_document_processor):
        """Test processing an empty directory."""
        processor = setup_document_processor
        
        # Mock glob to return an empty list
        with patch('pathlib.Path.glob', return_value=[]):
            results = processor.process_directory(
                directory_path="mock/path",
                pattern="*.json"
            )
            
            # Verify an empty list was returned
            assert results == []


class TestProcessDirectoryWithMongoDB:
    """Test the private _process_directory_with_mongodb method."""
    
    def test_process_directory_with_mongodb_batch(self, setup_document_processor):
        """Test batch processing with MongoDB."""
        processor = setup_document_processor
        
        # Create test files
        test_files = [
            Path("mock/path/file1.json"),
            Path("mock/path/file2.json"),
            Path("mock/path/file3.json")
        ]
        
        # Mock document_exists to return different values for different files
        processor.db_manager.document_exists.side_effect = [
            True,   # file1 exists
            False,  # file2 doesn't exist
            False   # file3 doesn't exist
        ]
        
        # Mock get_exam_metadata for existing document
        existing_metadata = {
            "examId": "file1",
            "subject": "Computer Science"
        }
        processor.db_manager.get_exam_metadata.return_value = existing_metadata
        
        # Mock extract_document_id to return different IDs
        processor.file_manager.extract_document_id.side_effect = ["file1", "file2", "file3"]
        
        # Process directory with a batch size that ensures a single bulk operation
        with patch.object(processor, '_prepare_metadata_for_db', return_value={"subject": "Computer Science"}):
            results = processor._process_directory_with_mongodb(
                file_paths=test_files,
                batch_size=3  # Use batch size of 3 to ensure a single batch for all files
            )
        
        # Verify document_exists was called for each file
        assert processor.db_manager.document_exists.call_count == 3
        
        # Verify get_exam_metadata was called for the existing document
        processor.db_manager.get_exam_metadata.assert_called_once_with("file1")
        
        # Verify bulk_save_exam_metadata was called once 
        # (since we're using a batch size equal to the number of files)
        assert processor.db_manager.bulk_save_exam_metadata.call_count == 1
        
        # Verify the call to bulk_save_exam_metadata included the right documents
        bulk_save_call = processor.db_manager.bulk_save_exam_metadata.call_args
        assert len(bulk_save_call[0][0]) == 2  # Two documents (file2 and file3)
        assert bulk_save_call[0][1] == ['file2', 'file3']  # Document IDs
        
        # Verify results contain status for all documents
        assert len(results) == 3
        assert any(r["status"] == "existing" for r in results)  # file1
        assert "file2" in [r["document_id"] for r in results]
        assert "file3" in [r["document_id"] for r in results]


class TestHelperMethods:
    """Test helper methods for MongoDB integration."""
    
    def test_prepare_metadata_for_db(self, setup_document_processor):
        """Test metadata preparation for MongoDB."""
        processor = setup_document_processor
        
        # Test metadata with standard fields
        metadata = {
            "Type": "Question Paper",
            "Subject": "Computer Science",
            "Qualification": "A2-Level",
            "Year": 2023,
            "Exam Season": "Summer",
            "Exam Paper": "Unit 3: Programming and System Development",
            "Exam Board": "WJEC"
        }
        
        db_metadata = processor._prepare_metadata_for_db(metadata)
        
        # Verify field mappings were applied
        assert "subject" in db_metadata
        assert db_metadata["subject"] == "Computer Science"
        assert "qualification" in db_metadata
        assert db_metadata["qualification"] == "A2-Level"
        assert "year" in db_metadata
        assert db_metadata["year"] == 2023
        assert "season" in db_metadata
        assert db_metadata["season"] == "Summer"
        assert "unit" in db_metadata
        assert db_metadata["unit"] == "Unit 3: Programming and System Development"
        assert "exam_board" in db_metadata
        assert db_metadata["exam_board"] == "WJEC"
        assert "paper_type" in db_metadata
        assert db_metadata["paper_type"] == "Question Paper"
    
    def test_prepare_metadata_for_db_missing_fields(self, setup_document_processor):
        """Test metadata preparation with missing fields."""
        processor = setup_document_processor
        
        # Test metadata with missing fields but with Date that contains year
        metadata = {
            "Type": "Question Paper",
            "Subject": "Computer Science",
            "Qualification": "A2-Level",
            # Missing Year
            "Date": "June 2023",
            "Exam Season": "Summer",
            # Missing Exam Paper
        }
        
        db_metadata = processor._prepare_metadata_for_db(metadata)
        
        # Verify year was extracted from Date
        assert "year" in db_metadata
        assert db_metadata["year"] == 2023
        
        # Verify other fields were properly mapped
        assert "subject" in db_metadata
        assert "qualification" in db_metadata
        assert "season" in db_metadata


if __name__ == "__main__":
    pytest.main(["-v"])