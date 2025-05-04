"""
Tests for the Document class.

This module contains comprehensive unit tests for the Document class, covering
the factory methods for creating Document instances from PDFs and database records.
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime, UTC
from bson import ObjectId

# Add the project root directory to sys.path if needed
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.Models.document import Document
from src.FileManager.file_manager import FileManager
from src.DBManager.db_manager import DBManager
from src.OCR.mistral_OCR_Client import MistralOCRClient


@pytest.fixture
def sample_pdf_file():
    """Create a temporary PDF file for testing."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf', mode='wb') as f:
        # Write some dummy PDF content
        f.write(b"%PDF-1.5\n%%EOF")
        pdf_path = f.name
    
    yield pdf_path
    
    # Clean up after test
    if os.path.exists(pdf_path):
        os.remove(pdf_path)


@pytest.fixture
def mock_db_manager():
    """Create a mock DBManager instance."""
    mock_db = MagicMock(spec=DBManager)
    
    # Configure store_file_in_gridfs to return a mock file ID
    mock_db.store_file_in_gridfs.return_value = "mock_file_id_12345"
    
    # Configure get_collection to return a mock collection
    mock_collection = MagicMock()
    mock_db.get_collection.return_value = mock_collection
    
    # Configure the update_one result
    mock_result = MagicMock()
    mock_result.upserted_id = ObjectId()
    mock_result.modified_count = 1
    mock_collection.update_one.return_value = mock_result
    
    return mock_db


@pytest.fixture
def mock_file_manager(mock_db_manager):
    """Create a mock FileManager instance."""
    mock_fm = MagicMock(spec=FileManager)
    mock_fm.db_manager = mock_db_manager
    
    # Configure get_file_hash to return a predictable hash
    mock_fm.get_file_hash.return_value = "test_document_hash_123"
    
    # Configure check_document_exists with default False
    mock_fm.check_document_exists.return_value = False
    
    # Configure add_document_to_db_with_images to return the document ID
    mock_fm.add_document_to_db_with_images.return_value = "test_document_hash_123"
    
    return mock_fm


@pytest.fixture
def mock_ocr_client():
    """Create a mock MistralOCRClient instance."""
    mock_ocr = MagicMock(spec=MistralOCRClient)
    
    # Configure upload_pdf to return a mock response
    mock_upload_response = MagicMock()
    mock_upload_response.id = "mock_upload_id_123"
    mock_ocr.upload_pdf.return_value = mock_upload_response
    
    # Configure get_signed_url to return a mock response
    mock_signed_url_response = MagicMock()
    mock_signed_url_response.url = "https://example.com/signed-url"
    mock_ocr.get_signed_url.return_value = mock_signed_url_response
    
    # Configure ocr_pdf to return a mock OCR result
    mock_ocr_result = MagicMock()
    mock_page = MagicMock()
    mock_page.__dict__ = {"text": "Sample OCR text", "page_number": 1}
    mock_ocr_result.pages = [mock_page]
    mock_ocr.ocr_pdf.return_value = mock_ocr_result
    
    return mock_ocr


@pytest.fixture
def sample_document_data():
    """Create sample document data for testing."""
    return {
        "document_id": "test_document_hash_123",
        "document_type": "Question Paper",
        "pdf_filename": "sample_exam.pdf",
        "pdf_file_id": "mock_file_id_12345",
        "pdf_upload_date": datetime.now(UTC),
        "ocr_storage": "inline",
        "ocr_upload_date": datetime.now(UTC),
        "ocr_json": [{"text": "Sample OCR text", "page_number": 1}],
        "images": [
            {
                "image_id": "img_p0_0",
                "page": 0,
                "index": 0,
                "format": "jpeg",
                "storage": "inline",
                "data": "base64encodeddata"
            }
        ],
        "processed": False
    }


class TestDocumentInit:
    """Test the Document class constructor."""
    
    def test_document_initialization(self):
        """Test basic initialization of a Document object."""
        # Arrange
        document_id = "test_doc_123"
        pdf_filename = "test_file.pdf"
        document_type = "Question Paper"
        ocr_json = [{"text": "Test content", "page_number": 1}]
        
        # Act
        document = Document(
            document_id=document_id,
            pdf_filename=pdf_filename,
            document_type=document_type,
            ocr_json=ocr_json
        )
        
        # Assert
        assert document.document_id == document_id
        assert document.pdf_filename == pdf_filename
        assert document.document_type == document_type
        assert document.ocr_json == ocr_json
        assert document.images == []
        assert document.processed is False
        assert document._id is None
        
    def test_document_initialization_with_optional_params(self):
        """Test initialization of a Document object with all parameters."""
        # Arrange
        document_id = "test_doc_123"
        pdf_filename = "test_file.pdf"
        document_type = "Mark Scheme"
        ocr_json = [{"text": "Test content", "page_number": 1}]
        images = [{"image_id": "img1", "data": "base64data"}]
        processed = True
        pdf_file_id = "file_id_123"
        ocr_storage = "inline"
        pdf_upload_date = datetime.now(UTC)
        ocr_upload_date = datetime.now(UTC)
        _id = ObjectId()
        
        # Act
        document = Document(
            document_id=document_id,
            pdf_filename=pdf_filename,
            document_type=document_type,
            ocr_json=ocr_json,
            images=images,
            processed=processed,
            pdf_file_id=pdf_file_id,
            ocr_storage=ocr_storage,
            pdf_upload_date=pdf_upload_date,
            ocr_upload_date=ocr_upload_date,
            _id=_id
        )
        
        # Assert
        assert document.document_id == document_id
        assert document.pdf_filename == pdf_filename
        assert document.document_type == document_type
        assert document.ocr_json == ocr_json
        assert document.images == images
        assert document.processed is True
        assert document.pdf_file_id == pdf_file_id
        assert document.ocr_storage == ocr_storage
        assert document.pdf_upload_date == pdf_upload_date
        assert document.ocr_upload_date == ocr_upload_date
        assert document._id == _id


class TestDocumentFromPDF:
    """Test the Document.from_pdf factory method."""

    def test_create_new_document_from_pdf(self, sample_pdf_file, mock_db_manager, mock_file_manager, mock_ocr_client):
        """Test creating a new Document instance from a PDF file."""
        # Arrange
        document_id = "test_document_hash_123"
        
        # Act
        with patch('src.Models.document.FileManager', return_value=mock_file_manager):
            with patch('src.Models.document.DBManager', return_value=mock_db_manager):
                document = Document.from_pdf(
                    pdf_file=sample_pdf_file,
                    ocr_client=mock_ocr_client,
                    db_manager=mock_db_manager,
                    file_manager=mock_file_manager
                )
        
        # Assert
        assert document is not None
        assert document.document_id == document_id
        mock_file_manager.get_file_hash.assert_called_once()
        mock_file_manager.check_document_exists.assert_called_once_with(document_id)
    
    def test_auto_detect_document_type_question_paper(self, sample_pdf_file, mock_db_manager, mock_file_manager):
        """Test automatic detection of document type for a question paper."""
        # Arrange - Create a PDF with a filename that indicates it's a question paper
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf', prefix='exam_paper_', mode='wb') as f:
            f.write(b"%PDF-1.5\n%%EOF")
            paper_pdf_path = f.name
        
        try:
            # Act
            with patch('src.Models.document.FileManager', return_value=mock_file_manager):
                with patch('src.Models.document.DBManager', return_value=mock_db_manager):
                    document = Document.from_pdf(
                        pdf_file=paper_pdf_path,
                        db_manager=mock_db_manager,
                        file_manager=mock_file_manager
                    )
            
            # Assert
            assert document.document_type == "Question Paper"
        
        finally:
            # Clean up
            if os.path.exists(paper_pdf_path):
                os.remove(paper_pdf_path)
    
    def test_auto_detect_document_type_mark_scheme(self, mock_db_manager, mock_file_manager):
        """Test automatic detection of document type for a mark scheme."""
        # Arrange - Create a temporary file with a mark scheme name pattern
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf', prefix='ms_', mode='wb') as f:
            f.write(b"%PDF-1.5\n%%EOF")
            ms_pdf_path = f.name
        
        try:
            # Patch the FileManager and DBManager classes to return our mocks
            with patch('src.Models.document.FileManager', return_value=mock_file_manager):
                with patch('src.Models.document.DBManager', return_value=mock_db_manager):
                    # Call the from_pdf method with the mark scheme file path
                    with patch.object(Document, 'from_database', side_effect=ValueError("Not found")):
                        document = Document.from_pdf(
                            pdf_file=ms_pdf_path,
                            document_type=None,  # Let it auto-detect
                            db_manager=mock_db_manager,
                            file_manager=mock_file_manager
                        )
            
            # Assert
            assert document.document_type == "Mark Scheme"
        
        finally:
            # Clean up
            if os.path.exists(ms_pdf_path):
                os.remove(ms_pdf_path)
    
    def test_create_document_explicit_type(self, sample_pdf_file, mock_db_manager, mock_file_manager):
        """Test creating a document with explicitly specified document type."""
        # Act
        with patch('src.Models.document.FileManager', return_value=mock_file_manager):
            with patch('src.Models.document.DBManager', return_value=mock_db_manager):
                document = Document.from_pdf(
                    pdf_file=sample_pdf_file,
                    document_type="Mark Scheme",
                    db_manager=mock_db_manager,
                    file_manager=mock_file_manager
                )
        
        # Assert
        assert document.document_type == "Mark Scheme"

    def test_retrieve_existing_document(self, sample_pdf_file, mock_db_manager, mock_file_manager, mock_ocr_client, sample_document_data):
        """Test retrieving an existing document when the PDF has already been processed."""
        # Arrange
        document_id = "test_document_hash_123"
        mock_file_manager.check_document_exists.return_value = True
        mock_file_manager.get_document_with_images.return_value = sample_document_data
        
        # Act
        with patch('src.Models.document.FileManager', return_value=mock_file_manager):
            with patch('src.Models.document.DBManager', return_value=mock_db_manager):
                document = Document.from_pdf(
                    pdf_file=sample_pdf_file,
                    ocr_client=mock_ocr_client,
                    db_manager=mock_db_manager,
                    file_manager=mock_file_manager
                )
        
        # Assert
        assert document is not None
        assert document.document_id == document_id
        mock_file_manager.get_file_hash.assert_called_once()
        mock_file_manager.check_document_exists.assert_called_once_with(document_id)
        mock_file_manager.get_document_with_images.assert_called_once_with(document_id)
        # Verify we didn't attempt to process the PDF again
        mock_db_manager.store_file_in_gridfs.assert_not_called()
    
    def test_gridfs_store_failure(self, sample_pdf_file, mock_db_manager, mock_file_manager):
        """Test error handling when storing in GridFS fails."""
        # Arrange
        mock_db_manager.store_file_in_gridfs.return_value = None  # Simulate failure
        
        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            with patch('src.Models.document.FileManager', return_value=mock_file_manager):
                with patch('src.Models.document.DBManager', return_value=mock_db_manager):
                    Document.from_pdf(
                        pdf_file=sample_pdf_file,
                        db_manager=mock_db_manager,
                        file_manager=mock_file_manager
                    )
        
        assert "Failed to store PDF in GridFS" in str(excinfo.value)
    
    def test_mongodb_store_failure(self, sample_pdf_file, mock_db_manager, mock_file_manager):
        """Test error handling when storing in MongoDB fails."""
        # Arrange
        mock_result = MagicMock()
        mock_result.upserted_id = None
        mock_result.modified_count = 0
        mock_db_manager.get_collection().update_one.return_value = mock_result
        
        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            with patch('src.Models.document.FileManager', return_value=mock_file_manager):
                with patch('src.Models.document.DBManager', return_value=mock_db_manager):
                    Document.from_pdf(
                        pdf_file=sample_pdf_file,
                        db_manager=mock_db_manager,
                        file_manager=mock_file_manager
                    )
        
        assert "Failed to store document in database" in str(excinfo.value)

    def test_error_handling_invalid_pdf(self, mock_db_manager, mock_file_manager, mock_ocr_client):
        """Test error handling when provided with an invalid PDF file."""
        # Arrange
        invalid_pdf_path = "/nonexistent/path/to/file.pdf"
        mock_file_manager.get_file_hash.side_effect = IOError("File not found")
        
        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            Document.from_pdf(
                pdf_file=invalid_pdf_path,
                ocr_client=mock_ocr_client,
                db_manager=mock_db_manager,
                file_manager=mock_file_manager
            )
        
        assert "Failed to create document from PDF" in str(excinfo.value)
        mock_file_manager.get_file_hash.assert_called_once()


class TestDocumentFromDatabase:
    """Test the Document.from_database factory method."""

    def test_retrieve_existing_document(self, mock_db_manager, mock_file_manager, sample_document_data):
        """Test retrieving a Document instance from the database."""
        # Arrange
        document_id = "test_document_hash_123"
        mock_file_manager.get_document_with_images.return_value = sample_document_data
        
        # Act
        with patch('src.Models.document.FileManager', return_value=mock_file_manager):
            with patch('src.Models.document.DBManager', return_value=mock_db_manager):
                document = Document.from_database(
                    document_id=document_id,
                    db_manager=mock_db_manager,
                    file_manager=mock_file_manager
                )
        
        # Assert
        assert document is not None
        assert document.document_id == document_id
        assert document.document_type == "Question Paper"
        assert document.pdf_filename == "sample_exam.pdf"
        assert len(document.ocr_json) == 1
        assert len(document.images) == 1
        mock_file_manager.get_document_with_images.assert_called_once_with(document_id)
    
    def test_retrieve_document_missing_fields(self, mock_db_manager, mock_file_manager):
        """Test retrieving a document with missing optional fields."""
        # Arrange
        document_id = "test_document_hash_123"
        minimal_document_data = {
            "document_id": document_id,
            # Missing many fields
        }
        mock_file_manager.get_document_with_images.return_value = minimal_document_data
        
        # Act
        with patch('src.Models.document.FileManager', return_value=mock_file_manager):
            with patch('src.Models.document.DBManager', return_value=mock_db_manager):
                document = Document.from_database(
                    document_id=document_id,
                    db_manager=mock_db_manager,
                    file_manager=mock_file_manager
                )
        
        # Assert
        assert document is not None
        assert document.document_id == document_id
        assert document.pdf_filename == ""  # Default value for missing field
        assert document.document_type == ""  # Default value for missing field
        assert document.ocr_json == []  # Default value for missing field
        assert document.images == []  # Default value for missing field
        assert document.processed is False  # Default value for missing field

    def test_nonexistent_document(self, mock_db_manager, mock_file_manager):
        """Test error handling when document doesn't exist in the database."""
        # Arrange
        document_id = "nonexistent_document_id"
        mock_file_manager.get_document_with_images.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            Document.from_database(
                document_id=document_id,
                db_manager=mock_db_manager,
                file_manager=mock_file_manager
            )
        
        assert f"Document with ID {document_id} not found" in str(excinfo.value)
        mock_file_manager.get_document_with_images.assert_called_once_with(document_id)

    def test_database_error(self, mock_db_manager, mock_file_manager):
        """Test error handling when a database error occurs."""
        # Arrange
        document_id = "test_document_hash_123"
        mock_file_manager.get_document_with_images.side_effect = Exception("Database connection error")
        
        # Act & Assert
        with pytest.raises(ValueError) as excinfo:
            Document.from_database(
                document_id=document_id,
                db_manager=mock_db_manager,
                file_manager=mock_file_manager
            )
        
        assert "Failed to retrieve document from database" in str(excinfo.value)
        mock_file_manager.get_document_with_images.assert_called_once_with(document_id)


class TestDocumentTypeDetection:
    """Test the document type detection helper method."""
    
    def test_mark_scheme_detection(self):
        """Test that mark scheme detection works with different filename patterns."""
        # Various filenames that should be detected as mark schemes
        ms_filenames = [
            "ms_example.pdf",
            "mark_scheme_physics.pdf",
            "CS-A2-U3-markscheme-2023.pdf",
            "Computer Science - MS - S21.pdf",
            "2500U10-1 WJEC GCE AS Comp Science Unit 1 MS S17.pdf"
        ]
        
        for filename in ms_filenames:
            assert Document._determine_document_type(filename) == "Mark Scheme"
    
    def test_question_paper_detection(self):
        """Test that question paper detection works with different filename patterns."""
        # Various filenames that should be detected as question papers
        qp_filenames = [
            "qp_example.pdf",
            "question_paper_chemistry.pdf",
            "CS-A2-U3-questionpaper-2023.pdf",
            "Computer Science - QP - S21.pdf",
            "2500U10-1 WJEC GCE AS Comp Science Unit 1 QP S17.pdf"
        ]
        
        for filename in qp_filenames:
            assert Document._determine_document_type(filename) == "Question Paper"
    
    def test_unknown_document_type(self):
        """Test that ambiguous filenames are marked as Unknown."""
        # Various filenames that should be marked as unknown
        unknown_filenames = [
            "computer_science_unit1.pdf",
            "2500U10-1.pdf",
            "CS-A2-U3-2023.pdf",
            "generic_file.pdf"
        ]
        
        for filename in unknown_filenames:
            assert Document._determine_document_type(filename) == "Unknown"


if __name__ == "__main__":
    pytest.main(["-v"])
