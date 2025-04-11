"""
Tests for the IndexManager class.

This module contains comprehensive unit tests for the IndexManager class, covering
all major functionality including index creation, document management, unit number detection,
relationship detection, hierarchical transformation, and search functionality.
"""

import os
import json
import tempfile
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Import the IndexManager class - conftest.py now handles the path setup
from src.IndexManager.index_manager import IndexManager


@pytest.fixture
def temp_index_file():
    """Create a temporary index file for testing."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as f:
        # Create a minimal valid index file
        json.dump({"documents": []}, f)
        path = f.name
    
    yield path
    
    # Clean up after the test
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def temp_hierarchical_index_file():
    """Create a temporary hierarchical index file for testing."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as f:
        # Create a minimal valid hierarchical index file
        json.dump({"subjects": {}}, f)
        path = f.name
    
    yield path
    
    # Clean up after the test
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def sample_index():
    """Create a sample index with test documents."""
    return {
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
                "related_documents": []
            },
            {
                "id": "s23-1500u30-1-ms",
                "type": "Mark Scheme",
                "year": 2023,
                "qualification": "GCE A Level",
                "subject": "Computer Science",
                "exam_paper": "Unit 3: Programming and System Development",
                "exam_season": "Summer",
                "content_path": "ocr_results/s23-1500u30-1-ms.json",
                "metadata_path": "ocr_results/metadata/s23-1500u30-1-ms-metadata.json",
                "unit_number": 3,
                "related_documents": []
            },
            {
                "id": "s23-2500u10-1",
                "type": "Question Paper",
                "year": 2023,
                "qualification": "AS Level",
                "subject": "Computer Science",
                "exam_paper": "Unit 1: Fundamentals of Computer Science",
                "exam_season": "Summer",
                "content_path": "ocr_results/s23-2500u10-1.json",
                "metadata_path": "ocr_results/metadata/s23-2500u10-1-metadata.json",
                "unit_number": 1,
                "related_documents": []
            },
            {
                "id": "no-unit-number",
                "type": "Question Paper",
                "year": 2023,
                "qualification": "AS Level",
                "subject": "Computer Science",
                "exam_paper": "Advanced Topics",
                "exam_season": "Summer",
                "content_path": "ocr_results/no-unit-number.json",
                "metadata_path": "ocr_results/metadata/no-unit-number-metadata.json",
                "related_documents": []
            }
        ]
    }


@pytest.fixture
def index_manager_with_data(temp_index_file, sample_index):
    """Create an IndexManager with sample data."""
    # Write the sample data to the temp file
    with open(temp_index_file, 'w') as f:
        json.dump(sample_index, f)
    
    # Create index manager with the temp file
    return IndexManager(temp_index_file)


class TestIndexManagerInit:
    """Test the initialization and basic functionality of IndexManager."""

    def test_init_with_existing_file(self, temp_index_file):
        """Test initialization with an existing index file."""
        manager = IndexManager(temp_index_file)
        assert manager.index == {"documents": []}
        assert manager.index_path == Path(temp_index_file)

    def test_init_with_nonexistent_file(self):
        """Test initialization with a non-existent file."""
        nonexistent_file = "/tmp/nonexistent_file.json"
        if os.path.exists(nonexistent_file):
            os.remove(nonexistent_file)
            
        manager = IndexManager(nonexistent_file)
        assert manager.index == {"documents": []}
        assert manager.index_path == Path(nonexistent_file)
        
    def test_init_with_corrupted_file(self, temp_index_file):
        """Test initialization with a corrupted JSON file."""
        # Write invalid JSON to the file
        with open(temp_index_file, 'w') as f:
            f.write("This is not valid JSON")
        
        manager = IndexManager(temp_index_file)
        assert manager.index == {"documents": []}


class TestUnitNumberExtraction:
    """Test the unit number extraction functionality."""

    def test_extract_unit_number_from_title(self):
        """Test extracting unit numbers from exam paper titles."""
        manager = IndexManager()
        
        # Test various formats of unit numbers in titles
        assert manager._extract_unit_number("Unit 3: Programming") == 3
        assert manager._extract_unit_number("unit 4 Development") == 4
        assert manager._extract_unit_number("UNIT5 Advanced Topics") == 5
        assert manager._extract_unit_number("Unit3: Data Structures") == 3
        
        # Test when no unit number is present
        assert manager._extract_unit_number("Advanced Topics") is None
        assert manager._extract_unit_number("") is None
        assert manager._extract_unit_number(None) is None

    def test_extract_unit_number_from_id(self):
        """Test extracting unit numbers from document IDs."""
        manager = IndexManager()
        
        # Test various formats of unit numbers in IDs
        assert manager._extract_unit_number("1500u30-1") == 3
        assert manager._extract_unit_number("1500U40-1") == 4
        assert manager._extract_unit_number("s23-2500u10-1") == 1
        assert manager._extract_unit_number("s23-2500U20-1a") == 2
        
        # Test when no unit number is present
        assert manager._extract_unit_number("exam-paper-2023") is None


class TestDocumentManagement:
    """Test document management functionality."""

    def test_find_document_by_id(self, index_manager_with_data):
        """Test finding documents by ID."""
        manager = index_manager_with_data
        
        # Test finding existing documents
        doc = manager.find_document_by_id("s23-1500u30-1")
        assert doc is not None
        assert doc["id"] == "s23-1500u30-1"
        assert doc["type"] == "Question Paper"
        
        # Test finding non-existent document
        assert manager.find_document_by_id("nonexistent-id") is None

    def test_update_index(self, index_manager_with_data):
        """Test adding or updating documents in the index."""
        manager = index_manager_with_data
        initial_count = len(manager.index["documents"])
        
        # Test adding a new document
        new_doc_metadata = {
            "Type": "Question Paper",
            "Year": 2024,
            "Qualification": "GCE A Level",
            "Subject": "Computer Science",
            "Exam Paper": "Unit 3: Programming and System Development",
            "Exam Season": "Summer"
        }
        
        manager.update_index(
            new_doc_metadata,
            "ocr_results/s24-1500u30-1.json",
            "ocr_results/metadata/s24-1500u30-1-metadata.json"
        )
        
        # Verify document was added
        assert len(manager.index["documents"]) == initial_count + 1
        added_doc = manager.find_document_by_id("s24-1500u30-1")
        assert added_doc is not None
        assert added_doc["year"] == 2024
        assert added_doc["unit_number"] == 3
        
        # Test updating an existing document
        updated_metadata = {
            "Type": "Question Paper",
            "Year": 2023,
            "Qualification": "GCE A Level Updated",
            "Subject": "Computer Science",
            "Exam Paper": "Unit 3: Updated Title",
            "Exam Season": "Winter"
        }
        
        manager.update_index(
            updated_metadata,
            "ocr_results/s23-1500u30-1.json",
            "ocr_results/metadata/s23-1500u30-1-metadata.json"
        )
        
        # Verify document was updated
        updated_doc = manager.find_document_by_id("s23-1500u30-1")
        assert updated_doc["qualification"] == "GCE A Level Updated"
        assert updated_doc["exam_paper"] == "Unit 3: Updated Title"
        assert updated_doc["exam_season"] == "Winter"
        
        # Verify document count remains unchanged after update
        assert len(manager.index["documents"]) == initial_count + 1


class TestRelationshipDetection:
    """Test document relationship detection functionality."""

    @patch.object(IndexManager, 'save_index')
    def test_update_related_documents_question_paper(self, mock_save, index_manager_with_data):
        """Test detecting related mark schemes for question papers."""
        manager = index_manager_with_data
        
        # Add a mark scheme with the expected naming pattern
        ms_doc = {
            "id": "s23-1500u30-1-ms",
            "type": "Mark Scheme",
            "year": 2023,
            "qualification": "GCE A Level",
            "subject": "Computer Science",
            "exam_paper": "Unit 3: Programming and System Development",
            "content_path": "ocr_results/s23-1500u30-1-ms.json",
            "metadata_path": "ocr_results/metadata/s23-1500u30-1-ms-metadata.json",
            "unit_number": 3,
            "related_documents": []
        }
        
        qp_doc = manager.find_document_by_id("s23-1500u30-1")
        
        # Update relationships
        manager._update_related_documents("s23-1500u30-1")
        
        # Check if relationship was established
        updated_qp = manager.find_document_by_id("s23-1500u30-1")
        updated_ms = manager.find_document_by_id("s23-1500u30-1-ms")
        
        assert "s23-1500u30-1-ms" in updated_qp["related_documents"]
        assert "s23-1500u30-1" in updated_ms["related_documents"]

    @patch.object(IndexManager, 'save_index')
    def test_update_related_documents_mark_scheme(self, mock_save, index_manager_with_data):
        """Test detecting related question papers for mark schemes."""
        manager = index_manager_with_data
        
        # Update relationships starting from mark scheme
        manager._update_related_documents("s23-1500u30-1-ms")
        
        # Check if relationship was established
        updated_qp = manager.find_document_by_id("s23-1500u30-1")
        updated_ms = manager.find_document_by_id("s23-1500u30-1-ms")
        
        assert "s23-1500u30-1-ms" in updated_qp["related_documents"]
        assert "s23-1500u30-1" in updated_ms["related_documents"]

    @patch.object(IndexManager, 'save_index')
    def test_find_related_by_unit(self, mock_save, index_manager_with_data):
        """Test finding related documents based on unit number."""
        manager = index_manager_with_data
        
        # Find related documents by unit
        related = manager.find_related_by_unit("s23-1500u30-1")
        
        # Verify related document is found
        assert len(related) == 1
        assert related[0]["id"] == "s23-1500u30-1-ms"
        
        # Verify relationships are updated in the index
        updated_qp = manager.find_document_by_id("s23-1500u30-1")
        updated_ms = manager.find_document_by_id("s23-1500u30-1-ms")
        
        assert "s23-1500u30-1-ms" in updated_qp["related_documents"]
        assert "s23-1500u30-1" in updated_ms["related_documents"]


class TestIndexOperations:
    """Test operations on the entire index."""

    def test_update_unit_numbers(self, index_manager_with_data):
        """Test updating unit numbers for all documents."""
        manager = index_manager_with_data
        
        # Add a document without a unit number but with unit in exam paper
        manager.index["documents"].append({
            "id": "missing-unit",
            "type": "Question Paper",
            "year": 2023,
            "qualification": "AS Level",
            "subject": "Computer Science",
            "exam_paper": "Unit 5: Advanced Programming",
            "content_path": "ocr_results/missing-unit.json",
            "metadata_path": "ocr_results/metadata/missing-unit-metadata.json",
            "related_documents": []
        })
        
        # Add a document without a unit number but with unit in ID
        manager.index["documents"].append({
            "id": "2500U60-1",
            "type": "Question Paper",
            "year": 2023,
            "qualification": "AS Level",
            "subject": "Computer Science",
            "exam_paper": "Advanced Topics",
            "content_path": "ocr_results/2500U60-1.json",
            "metadata_path": "ocr_results/metadata/2500U60-1-metadata.json",
            "related_documents": []
        })
        
        # Count documents without unit number initially
        initial_without_unit = len(manager.get_documents_without_unit())
        
        # Update unit numbers
        updated_count = manager.update_unit_numbers()
        
        # Verify unit numbers were added
        assert updated_count > 0
        
        # Check specific documents
        missing_unit_doc = manager.find_document_by_id("missing-unit")
        assert missing_unit_doc["unit_number"] == 5
        
        id_unit_doc = manager.find_document_by_id("2500U60-1")
        assert id_unit_doc["unit_number"] == 6
        
        # Verify fewer documents are now without unit numbers
        final_without_unit = len(manager.get_documents_without_unit())
        assert final_without_unit < initial_without_unit

    def test_sort_index(self, index_manager_with_data):
        """Test sorting the index by subject, year, qualification, and unit_number."""
        manager = index_manager_with_data
        
        # Add documents with varying sort criteria
        manager.index["documents"].extend([
            {
                "id": "older-doc",
                "type": "Question Paper",
                "year": 2020,
                "qualification": "GCE A Level",
                "subject": "Computer Science",
                "unit_number": 3
            },
            {
                "id": "different-subject",
                "type": "Question Paper",
                "year": 2023,
                "qualification": "GCE A Level",
                "subject": "Mathematics",
                "unit_number": 1
            }
        ])
        
        # Sort the index
        sorted_docs = manager.sort_index()
        
        # Verify sorting order
        assert sorted_docs[0]["subject"] == "Computer Science"  # Computer Science comes before Mathematics
        
        # Find positions of specific documents in the sorted list
        positions = {doc["id"]: i for i, doc in enumerate(sorted_docs)}
        
        # Verify the Mathematics document comes after Computer Science
        assert positions["different-subject"] > positions["s23-1500u30-1"]
        
        # Verify the older document comes before newer one in the same subject
        assert positions["older-doc"] < positions["s23-1500u30-1"]
        
        # Verify unit 1 comes before unit 3 within same subject/year
        assert positions["s23-2500u10-1"] < positions["s23-1500u30-1"]

    @patch('builtins.print')
    def test_get_unit_distribution(self, mock_print, index_manager_with_data):
        """Test getting distribution of documents by unit number."""
        manager = index_manager_with_data
        
        # Get unit distribution
        distribution = manager.get_unit_distribution()
        
        # Verify distribution counts
        assert distribution[1] == 1  # One Unit 1 document
        assert distribution[3] == 2  # Two Unit 3 documents

    def test_get_documents_without_unit(self, index_manager_with_data):
        """Test getting documents without unit numbers."""
        manager = index_manager_with_data
        
        # Get documents without unit
        docs_without_unit = manager.get_documents_without_unit()
        
        # Verify result
        assert len(docs_without_unit) == 1
        assert "no-unit-number" in docs_without_unit


class TestSearchFunctionality:
    """Test document search functionality."""

    def test_search_by_criteria(self, index_manager_with_data):
        """Test searching documents by metadata criteria."""
        manager = index_manager_with_data
        
        # Search by year and qualification
        results = manager.search_documents(criteria={
            "year": 2023,
            "qualification": "GCE A Level"
        })
        
        # Verify results
        assert len(results) == 2
        assert all(doc["year"] == 2023 and doc["qualification"] == "GCE A Level" for doc in results)
        
        # Search by type
        mark_schemes = manager.search_documents(criteria={"type": "Mark Scheme"})
        assert len(mark_schemes) == 1
        assert mark_schemes[0]["type"] == "Mark Scheme"
        
        # Search with no matches
        no_matches = manager.search_documents(criteria={"year": 2025})
        assert len(no_matches) == 0

    def test_search_by_query(self, index_manager_with_data):
        """Test searching documents by text query."""
        manager = index_manager_with_data
        
        # Search by exam paper title fragment
        results = manager.search_documents(query="Fundamentals")
        
        # Verify results
        assert len(results) == 1
        assert "Fundamentals" in results[0]["exam_paper"]
        
        # Search with no matches
        no_matches = manager.search_documents(query="Advanced Quantum Computing")
        assert len(no_matches) == 0

    def test_search_by_criteria_and_query(self, index_manager_with_data):
        """Test searching documents by both criteria and query."""
        manager = index_manager_with_data
        
        # Search by criteria and query
        results = manager.search_documents(
            criteria={"type": "Question Paper"},
            query="Unit"
        )
        
        # Verify results
        assert len(results) == 2  # Two question papers with "Unit" in their metadata
        assert all(doc["type"] == "Question Paper" for doc in results)
        assert all("Unit" in str(doc) for doc in results)


@pytest.mark.parametrize("interactive", [True, False])
class TestHierarchicalTransformation:
    """Test hierarchical transformation functionality."""

    @patch('builtins.print')
    @patch.object(IndexManager, '_validate_transformation', return_value=True)
    def test_transform_to_hierarchical(self, mock_validate, mock_print, interactive, index_manager_with_data, temp_hierarchical_index_file):
        """Test transforming flat index to hierarchical structure."""
        manager = index_manager_with_data
        
        # Perform transformation
        result = manager.transform_to_hierarchical(temp_hierarchical_index_file, interactive=interactive)
        
        # Verify structure has subjects
        assert "subjects" in result
        assert "Computer Science" in result["subjects"]
        
        # Verify year structure
        assert "years" in result["subjects"]["Computer Science"]
        assert "2023" in result["subjects"]["Computer Science"]["years"]
        
        # Verify qualification structure
        qualifications = result["subjects"]["Computer Science"]["years"]["2023"]["qualifications"]
        assert "GCE A Level" in qualifications
        assert "AS Level" in qualifications
        
        # Verify exams structure
        assert "exams" in qualifications["GCE A Level"]
        assert "Unit 3" in qualifications["GCE A Level"]["exams"]
        
        # Verify document inclusion
        unit3 = qualifications["GCE A Level"]["exams"]["Unit 3"]
        assert "documents" in unit3
        assert "Question Paper" in unit3["documents"]
        assert "Mark Scheme" in unit3["documents"]
        assert len(unit3["documents"]["Question Paper"]) == 1
        assert len(unit3["documents"]["Mark Scheme"]) == 1
        
        # Verify document content
        qp = unit3["documents"]["Question Paper"][0]
        assert qp["id"] == "s23-1500u30-1"
        
        # Verify file was created
        assert os.path.exists(temp_hierarchical_index_file)
        
        # Load the file and verify it matches the returned structure
        with open(temp_hierarchical_index_file, 'r') as f:
            saved_structure = json.load(f)
        
        assert saved_structure == result


class TestErrorHandling:
    """Test error handling in IndexManager."""

    def test_save_index_error(self):
        """Test error handling when saving index fails."""
        manager = IndexManager()
        
        # Try to save to an invalid location
        with pytest.raises(IOError):
            manager.save_index("/nonexistent_directory/file.json")

    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    def test_read_metadata_file_error(self, mock_open):
        """Test error handling when reading metadata file fails."""
        manager = IndexManager()
        
        # Should return None when file can't be read
        result = manager._read_metadata_file("some_file.json")
        assert result is None


if __name__ == "__main__":
    pytest.main(["-v"])