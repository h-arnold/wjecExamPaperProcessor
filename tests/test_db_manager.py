"""
Tests for the DBManager class.

This module contains comprehensive unit tests for the DBManager class, covering
all major functionality including initialization, connection handling,
database and collection retrieval, error handling, and connection closure.
"""

import os
import pytest
import sys
from unittest.mock import patch, MagicMock, call

# Add the project root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.DBManager.dbManager import DBManager
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError


@pytest.fixture
def mock_env_vars():
    """Set up environment variables for testing."""
    with patch.dict(os.environ, {
        "MONGODB_URI": "mongodb://test-connection-string",
        "MONGODB_DATABASE_NAME": "test-database",
        "MONGODB_TIMEOUT_MS": "3000"
    }):
        yield


@pytest.fixture
def mock_env_vars_partial():
    """Set up partial environment variables for testing."""
    with patch.dict(os.environ, {
        "MONGODB_URI": "mongodb://test-connection-string",
        # Missing MONGODB_DATABASE_NAME
    }, clear=True):
        yield


@pytest.fixture
def mock_mongodb_client():
    """Mock MongoDB client for testing."""
    with patch('src.DBManager.dbManager.MongoClient') as mock_client:
        # Set up mock client and database
        mock_db = MagicMock()
        mock_collection = MagicMock()
        
        # Configure mocks
        mock_client.return_value = MagicMock()
        mock_client.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        
        # Set up admin command for ping test
        mock_admin = MagicMock()
        mock_client.return_value.admin = mock_admin
        mock_admin.command.return_value = True
        
        yield mock_client, mock_db, mock_collection


class TestDBManagerInit:
    """Test the initialization and configuration of DBManager."""

    def test_init_with_parameters(self):
        """Test initialization with explicit parameters."""
        manager = DBManager(
            connection_string="mongodb://custom-connection",
            database_name="custom-database",
            timeout_ms=2000
        )
        
        assert manager.connection_string == "mongodb://custom-connection"
        assert manager.database_name == "custom-database"
        assert manager.timeout_ms == 2000
        assert manager.client is None
        assert manager.db is None

    def test_init_with_env_vars(self, mock_env_vars):
        """Test initialization with environment variables."""
        manager = DBManager()
        
        assert manager.connection_string == "mongodb://test-connection-string"
        assert manager.database_name == "test-database"
        assert manager.timeout_ms == 3000

    def test_init_with_mixed_params(self, mock_env_vars):
        """Test initialization with mix of parameters and environment variables."""
        manager = DBManager(database_name="override-database")
        
        assert manager.connection_string == "mongodb://test-connection-string"
        assert manager.database_name == "override-database"
        assert manager.timeout_ms == 3000

    def test_init_with_default_timeout(self, mock_env_vars):
        """Test initialization with default timeout when not provided."""
        # Clear the existing env vars and only set the ones we need for this test
        with patch.dict(os.environ, {
            "MONGODB_URI": "mongodb://test-connection-string",
            "MONGODB_DATABASE_NAME": "test-database",
            # No MONGODB_TIMEOUT_MS
        }, clear=True):
            manager = DBManager()
            assert manager.timeout_ms == 5000  # Default value

    def test_init_missing_connection_string(self):
        """Test initialization fails without connection string."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as excinfo:
                DBManager()
            assert "MongoDB connection string not provided" in str(excinfo.value)

    def test_init_missing_database_name(self):
        """Test initialization fails without database name."""
        # Mock load_dotenv to ensure it doesn't load any real .env file
        with patch('src.DBManager.dbManager.load_dotenv'):
            # Use a direct environment patch just for this test
            with patch.dict(os.environ, {
                "MONGODB_URI": "mongodb://test-connection-string",
                # Explicitly not setting MONGODB_DATABASE_NAME
            }, clear=True):
                with pytest.raises(ValueError) as excinfo:
                    DBManager()
                assert "MongoDB database name not provided" in str(excinfo.value)


class TestDBManagerConnection:
    """Test the connection functionality of DBManager."""

    def test_connect_success(self, mock_mongodb_client):
        """Test successful database connection."""
        mock_client, mock_db, _ = mock_mongodb_client
        
        manager = DBManager(
            connection_string="mongodb://test-success",
            database_name="test-db"
        )
        
        result = manager.connect()
        
        # Verify client was created with correct parameters
        mock_client.assert_called_once_with(
            "mongodb://test-success",
            serverSelectionTimeoutMS=5000
        )
        
        # Verify ping was called to test connection
        mock_client.return_value.admin.command.assert_called_once_with('ping')
        
        # Verify database was accessed
        mock_client.return_value.__getitem__.assert_called_once_with("test-db")
        
        # Verify correct database is returned
        assert result == mock_db
        assert manager.db == mock_db
        assert manager.client == mock_client.return_value

    def test_connect_connection_failure(self, mock_mongodb_client):
        """Test handling of connection failure."""
        mock_client, _, _ = mock_mongodb_client
        mock_client.return_value.admin.command.side_effect = ConnectionFailure("Connection error")
        
        manager = DBManager(
            connection_string="mongodb://test-fail",
            database_name="test-db"
        )
        
        with pytest.raises(ConnectionError) as excinfo:
            manager.connect()
        
        assert "Failed to connect to MongoDB Atlas" in str(excinfo.value)
        assert "Connection error" in str(excinfo.value)

    def test_connect_timeout(self, mock_mongodb_client):
        """Test handling of connection timeout."""
        mock_client, _, _ = mock_mongodb_client
        mock_client.return_value.admin.command.side_effect = ServerSelectionTimeoutError("Timeout")
        
        manager = DBManager(
            connection_string="mongodb://test-timeout",
            database_name="test-db"
        )
        
        with pytest.raises(ConnectionError) as excinfo:
            manager.connect()
        
        assert "Failed to connect to MongoDB Atlas" in str(excinfo.value)
        assert "Timeout" in str(excinfo.value)

    @patch.object(DBManager, 'connect')
    def test_get_database_existing(self, mock_connect):
        """Test get_database when connection already exists."""
        manager = DBManager(
            connection_string="mongodb://test",
            database_name="test-db"
        )
        
        # Simulate existing connection
        mock_db = MagicMock()
        manager.db = mock_db
        
        result = manager.get_database()
        
        # Verify connect was not called again
        mock_connect.assert_not_called()
        assert result == mock_db

    @patch.object(DBManager, 'connect')
    def test_get_database_new_connection(self, mock_connect):
        """Test get_database when connection doesn't exist."""
        mock_db = MagicMock()
        mock_connect.return_value = mock_db
        
        manager = DBManager(
            connection_string="mongodb://test",
            database_name="test-db"
        )
        
        result = manager.get_database()
        
        # Verify connect was called
        mock_connect.assert_called_once()
        assert result == mock_db

    def test_disconnect_method(self):
        """Test that disconnect() method properly closes the connection as an alias for close_connection()."""
        manager = DBManager(
            connection_string="mongodb://test",
            database_name="test-db"
        )
        
        # Mock client and database
        mock_client = MagicMock()
        manager.client = mock_client
        manager.db = MagicMock()
        
        # Spy on close_connection method to verify it gets called
        with patch.object(manager, 'close_connection', wraps=manager.close_connection) as spy_close:
            manager.disconnect()
            
            # Verify close_connection was called exactly once
            spy_close.assert_called_once()
            
            # Verify client was closed
            mock_client.close.assert_called_once()
            assert manager.client is None
            assert manager.db is None


class TestDBManagerOperations:
    """Test database operations of DBManager."""

    @patch.object(DBManager, 'get_database')
    def test_get_collection(self, mock_get_database):
        """Test retrieving a collection from the database."""
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_database.return_value = mock_db
        
        manager = DBManager(
            connection_string="mongodb://test",
            database_name="test-db"
        )
        
        result = manager.get_collection("test-collection")
        
        # Verify database was accessed
        mock_get_database.assert_called_once()
        mock_db.__getitem__.assert_called_once_with("test-collection")
        assert result == mock_collection

    def test_close_connection(self):
        """Test closing database connection."""
        manager = DBManager(
            connection_string="mongodb://test",
            database_name="test-db"
        )
        
        # Mock client and database
        mock_client = MagicMock()
        manager.client = mock_client
        manager.db = MagicMock()
        
        manager.close_connection()
        
        # Verify client was closed
        mock_client.close.assert_called_once()
        assert manager.client is None
        assert manager.db is None

    def test_close_connection_no_client(self):
        """Test closing connection when no client exists."""
        manager = DBManager(
            connection_string="mongodb://test",
            database_name="test-db"
        )
        
        # Ensure no client exists
        manager.client = None
        manager.db = None
        
        # Should not raise an exception
        manager.close_connection()


class TestExamMetadataOperations:
    """Test exam metadata CRUD operations of DBManager."""

    @patch.object(DBManager, 'get_collection')
    def test_save_exam_metadata_new_document(self, mock_get_collection):
        """Test saving new exam metadata."""
        # Setup mock collection and update_one result
        mock_collection = MagicMock()
        mock_result = MagicMock()
        mock_result.upserted_id = "new_id"  # Indicates a new document was created
        mock_result.matched_count = 0
        mock_collection.update_one.return_value = mock_result
        mock_get_collection.return_value = mock_collection
        
        # Create test metadata
        test_metadata = {
            'subject': 'Computer Science',
            'qualification': 'A2-Level',
            'year': 2023,
            'season': 'Summer',
            'unit': 'Unit 3',
            'exam_board': 'WJEC',
            'paper_type': 'Question Paper'
        }
        
        # Initialize manager and call method
        manager = DBManager(
            connection_string="mongodb://test",
            database_name="test-db"
        )
        
        doc_id = manager.save_exam_metadata(test_metadata)
        
        # Verify collection was accessed
        mock_get_collection.assert_called_once_with('exams')
        
        # Verify a generated examId was added
        assert 'examId' in test_metadata
        assert test_metadata['examId'] == 'Computer Science_A2-Level_Unit 3_2023_Summer'
        
        # Verify metadata contains processed_date
        assert 'metadata' in test_metadata
        assert 'processed_date' in test_metadata['metadata']
        
        # Verify update_one was called with correct parameters
        mock_collection.update_one.assert_called_once()
        # Get the first positional argument (query)
        call_args = mock_collection.update_one.call_args[0]
        assert call_args[0] == {'examId': test_metadata['examId']}
        
        # Verify correct ID was returned
        assert doc_id == test_metadata['examId']

    @patch.object(DBManager, 'get_collection')
    def test_save_exam_metadata_with_document_id(self, mock_get_collection):
        """Test saving exam metadata with explicitly provided document ID."""
        # Setup mock collection and update_one result
        mock_collection = MagicMock()
        mock_result = MagicMock()
        mock_result.upserted_id = None  # No new document was created
        mock_result.matched_count = 1   # Matched an existing document
        mock_collection.update_one.return_value = mock_result
        mock_get_collection.return_value = mock_collection
        
        # Create test metadata
        test_metadata = {
            'subject': 'Computer Science',
            'qualification': 'AS-Level',
            'year': 2023,
            'season': 'Summer',
            'unit': 'Unit 1',
            'exam_board': 'WJEC',
            'paper_type': 'Mark Scheme'
        }
        
        # Explicit document ID
        explicit_doc_id = "CS_AS_U1_2023_S_MS"
        
        # Initialize manager and call method
        manager = DBManager(
            connection_string="mongodb://test",
            database_name="test-db"
        )
        
        doc_id = manager.save_exam_metadata(test_metadata, explicit_doc_id)
        
        # Verify examId was set to explicit ID
        assert test_metadata['examId'] == explicit_doc_id
        
        # Verify update_one was called with correct parameters
        mock_collection.update_one.assert_called_once()
        call_args = mock_collection.update_one.call_args[0]
        assert call_args[0] == {'examId': explicit_doc_id}
        
        # Verify correct ID was returned
        assert doc_id == explicit_doc_id

    @patch.object(DBManager, 'get_collection')
    def test_save_exam_metadata_missing_fields(self, mock_get_collection):
        """Test saving exam metadata with missing required fields."""
        # Setup mock collection
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection
        
        # Create test metadata with missing fields
        test_metadata = {
            'subject': 'Computer Science',
            'qualification': 'AS-Level',
            # 'year': missing,
            'season': 'Summer',
            # 'unit': missing
        }
        
        # Initialize manager
        manager = DBManager(
            connection_string="mongodb://test",
            database_name="test-db"
        )
        
        # Should raise ValueError
        with pytest.raises(ValueError) as excinfo:
            manager.save_exam_metadata(test_metadata)
        
        assert "Metadata missing required fields" in str(excinfo.value)
        assert "year" in str(excinfo.value)
        assert "unit" in str(excinfo.value)
        
        # Verify update_one was not called
        mock_collection.update_one.assert_not_called()

    @patch.object(DBManager, 'get_collection')
    def test_get_exam_metadata_found(self, mock_get_collection):
        """Test retrieving exam metadata that exists."""
        # Setup mock collection and find_one result
        mock_collection = MagicMock()
        expected_doc = {
            'examId': 'test-doc-id',
            'subject': 'Computer Science',
            'qualification': 'A2-Level',
            'year': 2023,
            'season': 'Summer'
        }
        mock_collection.find_one.return_value = expected_doc
        mock_get_collection.return_value = mock_collection
        
        # Initialize manager and call method
        manager = DBManager(
            connection_string="mongodb://test",
            database_name="test-db"
        )
        
        result = manager.get_exam_metadata('test-doc-id')
        
        # Verify collection was accessed
        mock_get_collection.assert_called_once_with('exams')
        
        # Verify find_one was called with correct query
        mock_collection.find_one.assert_called_once_with({'examId': 'test-doc-id'})
        
        # Verify correct document was returned
        assert result == expected_doc

    @patch.object(DBManager, 'get_collection')
    def test_get_exam_metadata_not_found(self, mock_get_collection):
        """Test retrieving exam metadata that doesn't exist."""
        # Setup mock collection and find_one result
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = None
        mock_get_collection.return_value = mock_collection
        
        # Initialize manager and call method
        manager = DBManager(
            connection_string="mongodb://test",
            database_name="test-db"
        )
        
        result = manager.get_exam_metadata('nonexistent-id')
        
        # Verify collection was accessed
        mock_get_collection.assert_called_once_with('exams')
        
        # Verify find_one was called with correct query
        mock_collection.find_one.assert_called_once_with({'examId': 'nonexistent-id'})
        
        # Verify None was returned
        assert result is None

    @patch.object(DBManager, 'get_collection')
    def test_delete_exam_metadata_success(self, mock_get_collection):
        """Test successfully deleting exam metadata."""
        # Setup mock collection and delete_one result
        mock_collection = MagicMock()
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_collection.delete_one.return_value = mock_result
        mock_get_collection.return_value = mock_collection
        
        # Initialize manager and call method
        manager = DBManager(
            connection_string="mongodb://test",
            database_name="test-db"
        )
        
        result = manager.delete_exam_metadata('test-doc-id')
        
        # Verify collection was accessed
        mock_get_collection.assert_called_once_with('exams')
        
        # Verify delete_one was called with correct query
        mock_collection.delete_one.assert_called_once_with({'examId': 'test-doc-id'})
        
        # Verify True was returned (deletion successful)
        assert result is True

    @patch.object(DBManager, 'get_collection')
    def test_delete_exam_metadata_not_found(self, mock_get_collection):
        """Test deleting exam metadata that doesn't exist."""
        # Setup mock collection and delete_one result
        mock_collection = MagicMock()
        mock_result = MagicMock()
        mock_result.deleted_count = 0
        mock_collection.delete_one.return_value = mock_result
        mock_get_collection.return_value = mock_collection
        
        # Initialize manager and call method
        manager = DBManager(
            connection_string="mongodb://test",
            database_name="test-db"
        )
        
        result = manager.delete_exam_metadata('nonexistent-id')
        
        # Verify collection was accessed
        mock_get_collection.assert_called_once_with('exams')
        
        # Verify delete_one was called with correct query
        mock_collection.delete_one.assert_called_once_with({'examId': 'nonexistent-id'})
        
        # Verify False was returned (nothing was deleted)
        assert result is False

    @patch.object(DBManager, 'get_collection')
    def test_document_exists_true(self, mock_get_collection):
        """Test checking existence of a document that exists."""
        # Setup mock collection and count_documents result
        mock_collection = MagicMock()
        mock_collection.count_documents.return_value = 1
        mock_get_collection.return_value = mock_collection
        
        # Initialize manager and call method
        manager = DBManager(
            connection_string="mongodb://test",
            database_name="test-db"
        )
        
        result = manager.document_exists('existing-id')
        
        # Verify collection was accessed
        mock_get_collection.assert_called_once_with('exams')
        
        # Verify count_documents was called with correct query and limit
        mock_collection.count_documents.assert_called_once_with({'examId': 'existing-id'}, limit=1)
        
        # Verify True was returned
        assert result is True

    @patch.object(DBManager, 'get_collection')
    def test_document_exists_false(self, mock_get_collection):
        """Test checking existence of a document that doesn't exist."""
        # Setup mock collection and count_documents result
        mock_collection = MagicMock()
        mock_collection.count_documents.return_value = 0
        mock_get_collection.return_value = mock_collection
        
        # Initialize manager and call method
        manager = DBManager(
            connection_string="mongodb://test",
            database_name="test-db"
        )
        
        result = manager.document_exists('nonexistent-id')
        
        # Verify collection was accessed
        mock_get_collection.assert_called_once_with('exams')
        
        # Verify count_documents was called with correct query and limit
        mock_collection.count_documents.assert_called_once_with({'examId': 'nonexistent-id'}, limit=1)
        
        # Verify False was returned
        assert result is False

    @patch.object(DBManager, 'get_collection')
    def test_bulk_save_exam_metadata_success(self, mock_get_collection):
        """Test successfully saving multiple exam metadata records in bulk."""
        # Setup mock collection and bulk_write result
        mock_collection = MagicMock()
        mock_result = MagicMock()
        mock_result.upserted_count = 2
        mock_result.modified_count = 1
        mock_collection.bulk_write.return_value = mock_result
        mock_get_collection.return_value = mock_collection
        
        # Create test metadata list
        test_metadata_list = [
            {
                'subject': 'Computer Science',
                'qualification': 'A2-Level',
                'year': 2023,
                'season': 'Summer',
                'unit': 'Unit 3',
                'exam_board': 'WJEC',
                'paper_type': 'Question Paper'
            },
            {
                'subject': 'Computer Science',
                'qualification': 'A2-Level',
                'year': 2023,
                'season': 'Summer',
                'unit': 'Unit 3',
                'exam_board': 'WJEC',
                'paper_type': 'Mark Scheme'
            },
            {
                'subject': 'Computer Science',
                'qualification': 'AS-Level',
                'year': 2023,
                'season': 'Summer',
                'unit': 'Unit 1',
                'exam_board': 'WJEC',
                'paper_type': 'Question Paper'
            }
        ]
        
        # Initialize manager and call method
        manager = DBManager(
            connection_string="mongodb://test",
            database_name="test-db"
        )
        
        result_ids = manager.bulk_save_exam_metadata(test_metadata_list)
        
        # Verify collection was accessed
        mock_get_collection.assert_called_once_with('exams')
        
        # Verify generated examIds are returned
        assert len(result_ids) == 3
        assert result_ids[0] == 'Computer Science_A2-Level_Unit 3_2023_Summer'
        assert result_ids[1] == 'Computer Science_A2-Level_Unit 3_2023_Summer'
        assert result_ids[2] == 'Computer Science_AS-Level_Unit 1_2023_Summer'
        
        # Verify bulk_write was called
        mock_collection.bulk_write.assert_called_once()
        
        # Check that metadata records have processed_date set
        for metadata in test_metadata_list:
            assert 'metadata' in metadata
            assert 'processed_date' in metadata['metadata']

    @patch.object(DBManager, 'get_collection')
    def test_bulk_save_exam_metadata_with_document_ids(self, mock_get_collection):
        """Test bulk saving with explicitly provided document IDs."""
        # Setup mock collection and bulk_write result
        mock_collection = MagicMock()
        mock_result = MagicMock()
        mock_result.upserted_count = 0
        mock_result.modified_count = 3
        mock_collection.bulk_write.return_value = mock_result
        mock_get_collection.return_value = mock_collection
        
        # Create test metadata list
        test_metadata_list = [
            {
                'subject': 'Computer Science',
                'qualification': 'A2-Level',
                'year': 2023,
                'season': 'Summer',
                'unit': 'Unit 3',
                'exam_board': 'WJEC',
                'paper_type': 'Question Paper'
            },
            {
                'subject': 'Computer Science',
                'qualification': 'A2-Level',
                'year': 2023,
                'season': 'Summer',
                'unit': 'Unit 3',
                'exam_board': 'WJEC',
                'paper_type': 'Mark Scheme'
            }
        ]
        
        # Explicit document IDs
        document_ids = ["doc1", "doc2"]
        
        # Initialize manager and call method
        manager = DBManager(
            connection_string="mongodb://test",
            database_name="test-db"
        )
        
        result_ids = manager.bulk_save_exam_metadata(test_metadata_list, document_ids)
        
        # Verify collection was accessed
        mock_get_collection.assert_called_once_with('exams')
        
        # Verify explicit IDs were returned
        assert result_ids == document_ids
        
        # Verify examIds were set to the provided document_ids
        assert test_metadata_list[0]['examId'] == 'doc1'
        assert test_metadata_list[1]['examId'] == 'doc2'
        
        # Verify bulk_write was called
        mock_collection.bulk_write.assert_called_once()

    @patch.object(DBManager, 'get_collection')
    def test_bulk_save_exam_metadata_missing_fields(self, mock_get_collection):
        """Test bulk save with some records missing required fields."""
        # Setup mock collection
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection
        
        # Create test metadata list with one record missing fields
        test_metadata_list = [
            {
                'subject': 'Computer Science',
                'qualification': 'A2-Level',
                'year': 2023,
                'season': 'Summer',
                'unit': 'Unit 3'
            },
            {
                'subject': 'Computer Science',
                'qualification': 'A2-Level',
                # Missing 'year'
                'season': 'Summer',
                'unit': 'Unit 4'
            }
        ]
        
        # Initialize manager
        manager = DBManager(
            connection_string="mongodb://test",
            database_name="test-db"
        )
        
        # Should raise ValueError for the second record
        with pytest.raises(ValueError) as excinfo:
            manager.bulk_save_exam_metadata(test_metadata_list)
        
        assert "Metadata at index 1 missing required fields" in str(excinfo.value)
        assert "year" in str(excinfo.value)
        
        # Verify bulk_write was not called
        mock_collection.bulk_write.assert_not_called()

    @patch.object(DBManager, 'get_collection')
    def test_bulk_save_exam_metadata_document_ids_mismatch(self, mock_get_collection):
        """Test bulk save with mismatched document IDs length."""
        # Setup mock collection
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection
        
        # Create test metadata list
        test_metadata_list = [
            {
                'subject': 'Computer Science',
                'qualification': 'A2-Level',
                'year': 2023,
                'season': 'Summer',
                'unit': 'Unit 3'
            },
            {
                'subject': 'Computer Science',
                'qualification': 'A2-Level',
                'year': 2023,
                'season': 'Summer',
                'unit': 'Unit 4'
            }
        ]
        
        # Document IDs with different length than metadata list
        document_ids = ["doc1"]
        
        # Initialize manager
        manager = DBManager(
            connection_string="mongodb://test",
            database_name="test-db"
        )
        
        # Should raise ValueError due to mismatched lengths
        with pytest.raises(ValueError) as excinfo:
            manager.bulk_save_exam_metadata(test_metadata_list, document_ids)
        
        assert "Document IDs list length" in str(excinfo.value)
        assert "doesn't match metadata list length" in str(excinfo.value)
        
        # Verify bulk_write was not called
        mock_collection.bulk_write.assert_not_called()


if __name__ == "__main__":
    pytest.main(["-v"])