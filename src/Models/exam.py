from enum import Enum
from typing import Optional, Dict, Any
import logging



class Qualification(Enum):
    """Enumeration of possible qualification types."""
    AS_LEVEL = "AS-Level"
    A2_LEVEL = "A2-Level"
    GCSE = "GCSE"


class ExamSeason(Enum):
    """Enumeration of possible exam seasons."""
    AUTUMN = "Autumn"
    SPRING = "Spring"
    SUMMER = "Summer"


class Exam:
    """
    Represents metadata extracted from an exam document (question paper or mark scheme).
    
    This class encapsulates the structured metadata from WJEC exam papers as defined
    in the metadata extraction prompt.
    """

    def __init__(
        self,
        exam_id: str,
        qualification: Qualification,
        year: int,
        subject: str,
        unit_number: str,
        exam_season: ExamSeason,
        exam_length: str,
        information_for_candidates: Optional[str] = None,
        information_for_examiners: Optional[str] = None,
        total_marks: Optional[int] = None
    ):
        """
        Initialize an Exam object with metadata extracted from an exam document.

        Args:
            exam_id: Unique identifier for the exam
            qualification: Level of qualification (AS-Level, A2-Level, GCSE)
            year: The year when the exam was published
            subject: The subject of the exam (always Computer Science)
            unit_number: The unit or paper number
            exam_season: Season when the exam takes place (Autumn, Spring, Summer)
            exam_length: Duration of the exam in format "X hours Y minutes"
            information_for_candidates: Optional instructions for candidates
            information_for_examiners: Optional instructions for examiners
            total_marks: Optional total number of marks available
        """
        self.exam_id = exam_id
        self.qualification = qualification
        self.year = year
        self.subject = subject
        self.unit_number = unit_number
        self.exam_season = exam_season
        self.exam_length = exam_length
        self.information_for_candidates = information_for_candidates
        self.information_for_examiners = information_for_examiners
        self.total_marks = total_marks

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Exam':
        """
        Create an Exam instance from a dictionary representation.

        Args:
            data: Dictionary containing exam metadata fields

        Returns:
            An Exam instance with the specified metadata
        """
        return cls(
            exam_id=data["Exam ID"],
            qualification=Qualification(data["Qualification"]),
            year=data["Year"],
            subject=data["Subject"],
            unit_number=data["Unit Number"],
            exam_season=ExamSeason(data["Exam Season"]),
            exam_length=data["Exam Length"],
            information_for_candidates=data.get("Information for Candidates"),
            information_for_examiners=data.get("Information for Examiners"),
            total_marks=data.get("Total Marks")
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the Exam instance to a dictionary representation.

        Returns:
            Dictionary containing all non-None exam metadata fields
        """
        result = {
            "Exam ID": self.exam_id,
            "Qualification": self.qualification.value,
            "Year": self.year,
            "Subject": self.subject,
            "Unit Number": self.unit_number,
            "Exam Season": self.exam_season.value,
            "Exam Length": self.exam_length
        }

        # Add optional fields only if they exist
        if self.information_for_candidates:
            result["Information for Candidates"] = self.information_for_candidates
        
        if self.information_for_examiners:
            result["Information for Examiners"] = self.information_for_examiners
        
        if self.total_marks is not None:
            result["Total Marks"] = self.total_marks

        return result
        
    @classmethod
    def get_by_id(cls, exam_id: str, subject: str) -> Optional['Exam']:
        """
        Retrieve an exam from the database by its ID.
        
        Args:
            exam_id: The unique identifier of the exam to retrieve
            subject: The subject of the exam (determines collection)
            
        Returns:
            An Exam instance if found, None otherwise
            
        Raises:
            ImportError: If the ExamRepository import fails
        """
        try:
            # Import here to avoid circular imports
            from src.DBManager.exam_repository import ExamRepository
            
            # Create repository instance
            exam_repository = ExamRepository()
            
            # Retrieve the exam
            return exam_repository.get_exam(exam_id, subject)
        except ImportError as e:
            logging.error(f"Failed to import required modules: {e}")
            raise
        except Exception as e:
            logging.error(f"Error retrieving exam {exam_id}: {e}")
            return None
            
    @classmethod
    def get_by_exam_details(
        cls,
        subject: str,
        year: int,
        qualification: Qualification,
        exam_season: ExamSeason,
        unit_number: str,
        create_if_not_found: bool = False
    ) -> Optional['Exam']:
        """
        Retrieve an exam from the database by its details or create it if not found.
        
        Args:
            subject: The subject of the exam (determines collection)
            year: The year of the exam
            qualification: The qualification level (AS, A2, GCSE)
            exam_season: The season when the exam was held
            unit_number: The unit or paper number
            create_if_not_found: Whether to create a new exam if not found (default: False)
            
        Returns:
            An Exam instance if found or created, None otherwise
            
        Raises:
            ImportError: If the ExamRepository import fails
        """
        try:
            # Import here to avoid circular imports
            from src.DBManager.exam_repository import ExamRepository
            
            # Create repository instance
            exam_repository = ExamRepository()
            
            # Define search criteria
            criteria = {
                "Year": year,
                "Qualification": qualification.value,
                "Exam Season": exam_season.value,
                "Unit Number": unit_number
            }
            
            # Attempt to find the exam
            exams = exam_repository.get_exams_by_criteria(subject, criteria)
            
            if exams:
                # Return the first matching exam
                return exams[0]
            elif create_if_not_found:
                # Generate an exam ID based on details
                exam_id = f"{subject}_{qualification.value}_{year}_{exam_season.value}_{unit_number}"
                
                # Create a new exam instance
                new_exam = cls(
                    exam_id=exam_id,
                    qualification=qualification,
                    year=year,
                    subject=subject,
                    unit_number=unit_number,
                    exam_season=exam_season,
                    exam_length="Unknown"  # Default value, should be updated later
                )
                
                # Save to database
                success = exam_repository.create_exam(new_exam)
                
                if success:
                    logging.info(f"Created new exam with ID: {exam_id}")
                    return new_exam
                else:
                    logging.error(f"Failed to create new exam with ID: {exam_id}")
                    return None
            
            # Not found and not creating a new one
            return None
            
        except ImportError as e:
            logging.error(f"Failed to import required modules: {e}")
            raise
        except Exception as e:
            logging.error(f"Error retrieving/creating exam: {e}")
            return None
