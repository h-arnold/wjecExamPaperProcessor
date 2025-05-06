"""
Base repository for WJEC Exam Paper Processor.

This module provides a base repository class that defines common database
operations, to be extended by specific repository implementations.
"""

import logging
from typing import Dict, Any, List, Optional, Callable, TypeVar, Generic, Union

from src.DBManager.db_manager import DBManager

T = TypeVar('T')

class BaseRepository(Generic[T]):
    """
    Base repository providing common database operations.
    
    This class implements common CRUD operations and error handling
    patterns to be inherited by specific repository implementations.
    It provides a consistent interface for database access.
    """
    
    def __init__(self, db_manager: DBManager, collection_name: Optional[str] = None):
        """
        Initialise the repository with a database manager instance.
        
        Args:
            db_manager: The database manager to use for database operations
            collection_name: Optional fixed collection name for this repository
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        self._collection = None
        self._collection_name = collection_name
        self.collection_cache = {}  # For repositories that use multiple collections
    
    @property
    def collection(self):
        """
        Get the default collection for this repository.
        
        Returns:
            The MongoDB collection or None if no collection name was provided
        """
        if self._collection is None and self._collection_name:
            self._collection = self.db_manager.get_collection(self._collection_name)
        return self._collection
    
    def _get_collection(self, collection_identifier: Optional[str] = None):
        """
        Get a collection by name or use the default collection.
        
        Args:
            collection_identifier: Optional identifier for the collection
            
        Returns:
            The MongoDB collection
        """
        if collection_identifier:
            if collection_identifier not in self.collection_cache:
                # Sanitize collection name if needed
                sanitized_name = collection_identifier.replace(" ", "_").lower()
                self.collection_cache[collection_identifier] = self.db_manager.get_collection(sanitized_name)
            return self.collection_cache[collection_identifier]
        return self.collection
    
    def _execute_with_error_handling(self, operation: Callable, error_message: str, *args, **kwargs):
        """
        Execute a database operation with standardised error handling.
        
        Args:
            operation: The function to execute
            error_message: The error message to log if an exception occurs
            args: Positional arguments to pass to the operation
            kwargs: Keyword arguments to pass to the operation
            
        Returns:
            The result of the operation or None if an error occurred
        """
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            self.logger.error(f"{error_message}: {str(e)}")
            return None
    
    def exists(self, id_field: str, id_value: str, 
               collection_identifier: Optional[str] = None) -> bool:
        """
        Check if a document with the given ID exists in the database.
        
        Args:
            id_field: The field name that contains the ID
            id_value: The ID value to check
            collection_identifier: Optional identifier for the collection
            
        Returns:
            bool: True if the document exists, False otherwise
        """
        def _check_exists():
            collection = self._get_collection(collection_identifier)
            if collection is None:
                return False
                
            # Count documents matching the ID (limit to 1 for efficiency)
            count = collection.count_documents({id_field: id_value}, limit=1)
            return count > 0
            
        return self._execute_with_error_handling(
            _check_exists,
            f"Error checking if document exists with {id_field}={id_value}"
        ) or False  # Return False if None is returned due to an error
    
    def get_by_id(self, id_field: str, id_value: str, 
                collection_identifier: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document from the database by ID.
        
        Args:
            id_field: The field name that contains the ID
            id_value: The ID value to retrieve
            collection_identifier: Optional identifier for the collection
            
        Returns:
            dict: The document data or None if not found
        """
        def _get_by_id():
            collection = self._get_collection(collection_identifier)
            if collection is None:
                self.logger.error(f"Failed to access collection {collection_identifier or self._collection_name}")
                return None
            
            # Retrieve the document from the database
            return collection.find_one({id_field: id_value})
            
        return self._execute_with_error_handling(
            _get_by_id,
            f"Error retrieving document with {id_field}={id_value}"
        )
    
    def get_many(self, criteria: Dict[str, Any], 
               collection_identifier: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve documents matching specified criteria.
        
        Args:
            criteria: Dictionary of field-value pairs to match
            collection_identifier: Optional identifier for the collection
            
        Returns:
            List[Dict]: List of matching documents
        """
        def _get_many():
            collection = self._get_collection(collection_identifier)
            if collection is None:
                self.logger.error(f"Failed to access collection {collection_identifier or self._collection_name}")
                return []
            
            # Find all matching documents
            return list(collection.find(criteria))
            
        result = self._execute_with_error_handling(
            _get_many,
            f"Error retrieving documents with criteria {criteria}"
        )
        
        return result or []  # Return empty list if None is returned due to an error
    
    def create_or_update(self, id_field: str, id_value: str, document: Dict[str, Any],
                      collection_identifier: Optional[str] = None) -> bool:
        """
        Create or update a document in the database.
        
        Args:
            id_field: The field name that contains the ID
            id_value: The ID value to create/update
            document: The document data to store
            collection_identifier: Optional identifier for the collection
            
        Returns:
            bool: True if creation/update was successful, False otherwise
        """
        def _create_or_update():
            collection = self._get_collection(collection_identifier)
            if collection is None:
                self.logger.error(f"Failed to access collection {collection_identifier or self._collection_name}")
                return False
                
            result = collection.update_one(
                {id_field: id_value},
                {'$set': document},
                upsert=True
            )
            
            success = bool(result.upserted_id or result.modified_count > 0)
            if success:
                self.logger.info(f"Document with {id_field}={id_value} created/updated successfully")
            
            return success
            
        return self._execute_with_error_handling(
            _create_or_update,
            f"Error creating/updating document with {id_field}={id_value}"
        ) or False  # Return False if None is returned due to an error
    
    def update(self, id_field: str, id_value: str, update_fields: Dict[str, Any],
             collection_identifier: Optional[str] = None) -> bool:
        """
        Update a document in the database.
        
        Args:
            id_field: The field name that contains the ID
            id_value: The ID value to update
            update_fields: Dictionary of fields to update
            collection_identifier: Optional identifier for the collection
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        def _update():
            collection = self._get_collection(collection_identifier)
            if collection is None:
                self.logger.error(f"Failed to access collection {collection_identifier or self._collection_name}")
                return False
                
            result = collection.update_one(
                {id_field: id_value},
                {"$set": update_fields}
            )
            
            success = result.modified_count > 0
            if success:
                self.logger.info(f"Document with {id_field}={id_value} updated successfully")
            else:
                self.logger.info(f"No changes made to document with {id_field}={id_value} (may not exist or state already up-to-date)")
                
            return success
            
        return self._execute_with_error_handling(
            _update,
            f"Error updating document with {id_field}={id_value}"
        ) or False  # Return False if None is returned due to an error
    
    def delete(self, id_field: str, id_value: str,
              collection_identifier: Optional[str] = None) -> bool:
        """
        Delete a document from the database.
        
        Args:
            id_field: The field name that contains the ID
            id_value: The ID value to delete
            collection_identifier: Optional identifier for the collection
            
        Returns:
            bool: True if document was deleted, False otherwise
        """
        def _delete():
            collection = self._get_collection(collection_identifier)
            if collection is None:
                self.logger.error(f"Failed to access collection {collection_identifier or self._collection_name}")
                return False
                
            # Delete the document
            result = collection.delete_one({id_field: id_value})
            
            deleted = result.deleted_count > 0
            if deleted:
                self.logger.info(f"Successfully deleted document with {id_field}={id_value}")
            else:
                self.logger.warning(f"Document with {id_field}={id_value} was not found in database")
            
            return deleted
            
        return self._execute_with_error_handling(
            _delete,
            f"Error deleting document with {id_field}={id_value}"
        ) or False  # Return False if None is returned due to an error
    
    def get_all(self, collection_identifier: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve all documents in a collection.
        
        Args:
            collection_identifier: Optional identifier for the collection
            
        Returns:
            List[Dict]: List of all documents in the collection
        """
        return self.get_many({}, collection_identifier)