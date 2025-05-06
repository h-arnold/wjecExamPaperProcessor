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
    
    This class implements common CRUD operations using the DBManager's
    run_query method, providing a consistent interface for database access
    while avoiding duplicated error handling logic.
    """
    
    def __init__(self, collection_name: Optional[str] = None):
        """
        Initialise the repository with a collection name.
        
        This class automatically uses the DBManager singleton instance.
        
        Args:
            collection_name: Optional fixed collection name for this repository
        """
        self.db_manager = DBManager.get_instance()
        self.logger = logging.getLogger(__name__)
        self._collection_name = collection_name
        self.collection_cache = {}  # For repositories that use multiple collections
    
    def _get_collection_name(self, collection_identifier: Optional[str] = None):
        """
        Get the appropriate collection name based on the identifier or default.
        
        Args:
            collection_identifier: Optional identifier for the collection
            
        Returns:
            str: The collection name to use
        """
        if collection_identifier:
            # Sanitize collection name if needed
            return collection_identifier.replace(" ", "_").lower()
        
        if not self._collection_name:
            raise ValueError("No collection name provided for repository operation")
            
        return self._collection_name
    
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
        collection_name = self._get_collection_name(collection_identifier)
        result = self.db_manager.run_query(
            collection_name, 'count', {id_field: id_value}, limit=1
        )
        
        return result is not None and result > 0
    
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
        collection_name = self._get_collection_name(collection_identifier)
        return self.db_manager.run_query(
            collection_name, 'find_one', {id_field: id_value}
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
        collection_name = self._get_collection_name(collection_identifier)
        result = self.db_manager.run_query(
            collection_name, 'find', criteria
        )
        
        return result or []
    
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
        collection_name = self._get_collection_name(collection_identifier)
        result = self.db_manager.run_query(
            collection_name, 'update_one', 
            {id_field: id_value}, {'$set': document}, 
            sort=[('upsert', True)]  # Using sort parameter to pass upsert flag
        )
        
        if result:
            success = bool(result.get('upserted_id') or result.get('modified_count', 0) > 0)
            if success:
                self.logger.info(f"Document with {id_field}={id_value} created/updated successfully")
            return success
            
        return False
    
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
        collection_name = self._get_collection_name(collection_identifier)
        result = self.db_manager.run_query(
            collection_name, 'update_one', 
            {id_field: id_value}, {'$set': update_fields}
        )
        
        if result:
            success = result.get('modified_count', 0) > 0
            if success:
                self.logger.info(f"Document with {id_field}={id_value} updated successfully")
            else:
                self.logger.info(f"No changes made to document with {id_field}={id_value} (may not exist or state already up-to-date)")
            return success
            
        return False
    
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
        collection_name = self._get_collection_name(collection_identifier)
        result = self.db_manager.run_query(
            collection_name, 'delete_one', {id_field: id_value}
        )
        
        if result:
            deleted = result.get('deleted_count', 0) > 0
            if deleted:
                self.logger.info(f"Successfully deleted document with {id_field}={id_value}")
            else:
                self.logger.warning(f"Document with {id_field}={id_value} was not found in database")
            return deleted
            
        return False
    
    def get_all(self, collection_identifier: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve all documents in a collection.
        
        Args:
            collection_identifier: Optional identifier for the collection
            
        Returns:
            List[Dict]: List of all documents in the collection
        """
        return self.get_many({}, collection_identifier)