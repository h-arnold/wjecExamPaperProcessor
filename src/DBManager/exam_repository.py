"""
Exam repository for WJEC Exam Paper Processor.

This module provides a repository for exam operations, separating
database access logic from the Exam domain model.
"""

import logging
from typing import Dict, Any, List, Optional

from src.DBManager.base_repository import BaseRepository
from src.Models.exam import Exam, Qualification, ExamSeason

class ExamRepository(BaseRepository[Exam]):
    """
    Repository for exam-related database operations.
    
    This class handles all database interactions for exam objects,
    providing methods for saving, retrieving, and deleting exams.
    The exams are stored in collections named after their subject
    to improve query performance for subject-specific searches.
    """
    
    def __init__(self):
        """
        Initialise the exam repository.
        
        The repository uses the BaseRepository's DBManager instance.
        """
        super().__init__()
    
    def check_exam_exists(self, exam_id: str, subject: str) -> bool:
        """
        Check if an exam with the given ID exists in the database.
        
        Args:
            exam_id: The exam ID to check
            subject: The subject of the exam (determines collection)
            
        Returns:
            bool: True if the exam exists, False otherwise
        """
        return self.exists("Exam ID", exam_id, subject)
    
    def get_exam(self, exam_id: str, subject: str) -> Optional[Exam]:
        """
        Retrieve an exam from the database by ID.
        
        Args:
            exam_id: The exam ID to retrieve
            subject: The subject of the exam (determines collection)
            
        Returns:
            Exam: The exam object or None if not found
        """
        exam_data = self.get_by_id("Exam ID", exam_id, subject)
        
        if exam_data:
            # Convert MongoDB _id to string if present and remove it
            if "_id" in exam_data:
                exam_data.pop("_id")
            
            # Create and return Exam object from data
            return Exam.from_dict(exam_data)
        
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
        exams_data = self.get_many(criteria, subject)
        
        # Convert to Exam objects
        exams = []
        for exam_data in exams_data:
            # Convert MongoDB _id to string if present and remove it
            if "_id" in exam_data:
                exam_data.pop("_id")
            
            # Create Exam object from data
            exams.append(Exam.from_dict(exam_data))
        
        return exams
    
    def create_exam(self, exam: Exam) -> bool:
        """
        Create a new exam record in the database.
        
        Args:
            exam: The Exam object to store
            
        Returns:
            bool: True if creation was successful, False otherwise
        """
        # Convert Exam object to dictionary
        exam_data = exam.to_dict()
        
        return self.create_or_update('Exam ID', exam.exam_id, exam_data, exam.subject)
    
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
        return self.update("Exam ID", exam_id, update_fields, subject)
    
    def delete_exam(self, exam_id: str, subject: str) -> bool:
        """
        Delete an exam from the database.
        
        Args:
            exam_id: The exam ID to delete
            subject: The subject of the exam (determines collection)
            
        Returns:
            bool: True if exam was deleted, False otherwise
        """
        return self.delete("Exam ID", exam_id, subject)
            
    def get_all_exams_for_subject(self, subject: str) -> List[Exam]:
        """
        Retrieve all exams for a specific subject.
        
        Args:
            subject: The subject to retrieve exams for
            
        Returns:
            List[Exam]: List of all exams for the subject
        """
        return self.get_exams_by_criteria(subject, {})
