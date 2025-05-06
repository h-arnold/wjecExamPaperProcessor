"""
Exam repository for WJEC Exam Paper Processor.

This module provides a repository for exam operations, separating
database access logic from the Exam domain model.
"""

import logging
from typing import Dict, Any, List, Optional

from src.DBManager.db_manager import DBManager
from src.Models.exam import Exam, Qualification, ExamSeason

class ExamRepository:
    """
    Repository for exam-related database operations.
    
    This class handles all database interactions for exam objects,
    providing methods for saving, retrieving, and deleting exams.
    The exams are stored in collections named after their subject
    to improve query performance for subject-specific searches.
    """
    
    def __init__(self, db_manager: DBManager):
        """
        Initialise the exam repository with a database manager instance.
        
        Args:
            db_manager: The database manager to use for database operations
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        self.collection_cache = {}  # Cache collection objects by subject
    
    def _get_collection_for_subject(self, subject: str):
        """
        Get or create a collection for the specified subject.
        
        Args:
            subject: The subject name to use as collection name
            
        Returns:
            The MongoDB collection for the subject
        """
        if subject not in self.collection_cache:
            # Sanitize collection name (replace spaces and special chars)
            collection_name = subject.replace(" ", "_").lower()
            self.collection_cache[subject] = self.db_manager.get_collection(collection_name)
        
        return self.collection_cache[subject]
    
    def check_exam_exists(self, exam_id: str, subject: str) -> bool:
        """
        Check if an exam with the given ID exists in the database.
        
        Args:
            exam_id: The exam ID to check
            subject: The subject of the exam (determines collection)
            
        Returns:
            bool: True if the exam exists, False otherwise
        """
        try:
            collection = self._get_collection_for_subject(subject)
            if collection is None:
                return False
                
            # Count exams matching the ID (limit to 1 for efficiency)
            count = collection.count_documents({"Exam ID": exam_id}, limit=1)
            return count > 0
            
        except Exception as e:
            # Log the error but return False rather than raising an exception
            self.logger.error(f"Error checking if exam exists: {str(e)}")
            return False
    
    def get_exam(self, exam_id: str, subject: str) -> Optional[Exam]:
        """
        Retrieve an exam from the database by ID.
        
        Args:
            exam_id: The exam ID to retrieve
            subject: The subject of the exam (determines collection)
            
        Returns:
            Exam: The exam object or None if not found
        """
        try:
            collection = self._get_collection_for_subject(subject)
            if collection is None:
                self.logger.error(f"Failed to access collection for subject {subject}")
                return None
            
            # Retrieve the exam from the database
            exam_data = collection.find_one({"Exam ID": exam_id})
            
            if exam_data:
                # Convert MongoDB _id to string if present and remove it
                if "_id" in exam_data:
                    exam_data.pop("_id")
                
                # Create and return Exam object from data
                return Exam.from_dict(exam_data)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error retrieving exam {exam_id} from database: {e}")
            return None
    
    def get_exams_by_criteria(self, subject: str, criteria: Dict[str, Any]) -> List[Exam]:
        """
        Retrieve exams matching specified criteria.
        
        Args:
            subject: The subject of the exams (determines collection)
            criteria: Dictionary of field-value pairs to match
            
        Returns:
            List[Exam]: List of matching exam objects
        """
        try:
            collection = self._get_collection_for_subject(subject)
            if collection is None:
                self.logger.error(f"Failed to access collection for subject {subject}")
                return []
            
            # Find all matching exams
            exams_data = collection.find(criteria)
            
            # Convert to Exam objects
            exams = []
            for exam_data in exams_data:
                # Convert MongoDB _id to string if present and remove it
                if "_id" in exam_data:
                    exam_data.pop("_id")
                
                # Create Exam object from data
                exams.append(Exam.from_dict(exam_data))
            
            return exams
            
        except Exception as e:
            self.logger.error(f"Error retrieving exams with criteria {criteria}: {e}")
            return []
    
    def create_exam(self, exam: Exam) -> bool:
        """
        Create a new exam record in the database.
        
        Args:
            exam: The Exam object to store
            
        Returns:
            bool: True if creation was successful, False otherwise
        """
        try:
            # Convert Exam object to dictionary
            exam_data = exam.to_dict()
            
            # Store in appropriate collection
            collection = self._get_collection_for_subject(exam.subject)
            if collection is None:
                self.logger.error(f"Failed to access collection for subject {exam.subject}")
                return False
                
            result = collection.update_one(
                {'Exam ID': exam.exam_id},
                {'$set': exam_data},
                upsert=True
            )
            
            success = bool(result.upserted_id or result.modified_count > 0)
            if success:
                self.logger.info(f"Exam {exam.exam_id} created/updated successfully")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error creating exam record: {str(e)}")
            return False
    
    def update_exam(self, exam_id: str, subject: str, update_fields: Dict[str, Any]) -> bool:
        """
        Update an exam in the database.
        
        Args:
            exam_id: The exam ID to update
            subject: The subject of the exam (determines collection)
            update_fields: Dictionary of fields to update
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            collection = self._get_collection_for_subject(subject)
            if collection is None:
                self.logger.error(f"Failed to access collection for subject {subject}")
                return False
                
            result = collection.update_one(
                {"Exam ID": exam_id},
                {"$set": update_fields}
            )
            
            success = result.modified_count > 0
            if success:
                self.logger.info(f"Exam {exam_id} updated successfully")
            else:
                self.logger.info(f"No changes made to exam {exam_id} (may not exist or state already up-to-date)")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating exam {exam_id}: {str(e)}")
            return False
    
    def delete_exam(self, exam_id: str, subject: str) -> bool:
        """
        Delete an exam from the database.
        
        Args:
            exam_id: The exam ID to delete
            subject: The subject of the exam (determines collection)
            
        Returns:
            bool: True if exam was deleted, False otherwise
        """
        try:
            collection = self._get_collection_for_subject(subject)
            if collection is None:
                self.logger.error(f"Failed to access collection for subject {subject}")
                return False
                
            # Delete the exam record
            result = collection.delete_one({"Exam ID": exam_id})
            
            deleted = result.deleted_count > 0
            if deleted:
                self.logger.info(f"Successfully deleted exam {exam_id} from database")
            else:
                self.logger.warning(f"Exam {exam_id} was not found in database")
            
            return deleted
            
        except Exception as e:
            self.logger.error(f"Error deleting exam {exam_id}: {str(e)}")
            return False
            
    def get_all_exams_for_subject(self, subject: str) -> List[Exam]:
        """
        Retrieve all exams for a specific subject.
        
        Args:
            subject: The subject to retrieve exams for
            
        Returns:
            List[Exam]: List of all exams for the subject
        """
        try:
            collection = self._get_collection_for_subject(subject)
            if collection is None:
                self.logger.error(f"Failed to access collection for subject {subject}")
                return []
            
            # Find all exams in the collection
            exams_data = collection.find({})
            
            # Convert to Exam objects
            exams = []
            for exam_data in exams_data:
                # Convert MongoDB _id to string if present and remove it
                if "_id" in exam_data:
                    exam_data.pop("_id")
                
                # Create Exam object from data
                exams.append(Exam.from_dict(exam_data))
            
            return exams
            
        except Exception as e:
            self.logger.error(f"Error retrieving all exams for subject {subject}: {e}")
            return []
