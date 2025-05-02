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


if __name__ == "__main__":
    pytest.main(["-v"])