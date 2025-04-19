"""
ExamContentParser - Module for parsing exam paper and mark scheme content.

This module processes OCR results from exam papers and mark schemes, extracts
structured question and mark scheme data using an LLM, and updates the hierarchical
index with the processed content including references to media files.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union

# Import related modules
from ..Prompts.question_and_markscheme_parser import QuestionAndMarkschemeParser
from ..Llm_client.mistral_client import MistralLLMClient


class ExamContentParser:
    """
    A class that orchestrates the parsing of exam papers and mark schemes.
    
    This class is responsible for:
    1. Loading question paper and mark scheme content
    2. Creating appropriate prompts using QuestionAndMarkschemeParser
    3. Submitting prompts to an LLM client
    4. Processing the responses
    5. Extracting media file references
    6. Updating the hierarchical index
    """
    
    def __init__(
        self,
        llm_client: MistralLLMClient,
        index_path: Union[str, Path],
        ocr_results_path: Union[str, Path],
        metadata_path: Union[str, Path],
        log_level: int = logging.INFO
    ):
        """
        Initialize the ExamContentParser.
        
        Args:
            llm_client (MistralLLMClient): Client for interacting with the Mistral LLM API
            index_path (Union[str, Path]): Path to the hierarchical index JSON file
            ocr_results_path (Union[str, Path]): Path to the directory containing OCR results
            metadata_path (Union[str, Path]): Path to the directory containing metadata files
            log_level (int): Logging level (default: logging.INFO)
        """
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
        
        # Ensure we have a console handler if none exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        # Store init parameters
        self.llm_client = llm_client
        self.index_path = Path(index_path)
        self.ocr_results_path = Path(ocr_results_path)
        self.metadata_path = Path(metadata_path)
        
        # Validate paths
        if not self.index_path.exists():
            raise FileNotFoundError(f"Index file not found at: {self.index_path}")
        if not self.ocr_results_path.exists():
            raise FileNotFoundError(f"OCR results directory not found at: {self.ocr_results_path}")
        if not self.metadata_path.exists():
            raise FileNotFoundError(f"Metadata directory not found at: {self.metadata_path}")
            
        self.logger.info("ExamContentParser initialized successfully")
    
    def parse_exam_content(self, question_paper_id: str, mark_scheme_id: str) -> bool:
        """
        Parse exam content for a given question paper and mark scheme.
        
        Args:
            question_paper_id (str): Identifier for the question paper
            mark_scheme_id (str): Identifier for the mark scheme
            
        Returns:
            bool: True if parsing and index update was successful, False otherwise
        """
        try:
            # 1. Load question paper and mark scheme content and metadata
            self.logger.info(f"Loading content for paper {question_paper_id} and mark scheme {mark_scheme_id}")
            
            qp_content, qp_metadata = self._load_exam_content_and_metadata(
                question_paper_id, "question_papers")
            ms_content, ms_metadata = self._load_exam_content_and_metadata(
                mark_scheme_id, "mark_schemes")
            
            # 2. Process content to extract questions and mark scheme data
            parsed_questions = self._process_exam_content(
                qp_content, qp_metadata, ms_content, ms_metadata)
            
            # 3. Add media file references
            self._add_media_file_references(parsed_questions, qp_content)
            
            # 4. Update the hierarchical index
            self._update_index(parsed_questions, qp_metadata)
            
            self.logger.info(f"Successfully processed exam paper {question_paper_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing exam content: {str(e)}", exc_info=True)
            return False
    
    def _load_exam_content_and_metadata(self, doc_id: str, metadata_subdir: str) -> Tuple[List[Dict], Dict]:
        """
        Load exam content and metadata for a given document ID.
        
        Args:
            doc_id (str): Document identifier
            metadata_subdir (str): Subdirectory within metadata path (e.g., "question_papers")
            
        Returns:
            Tuple[List[Dict], Dict]: Tuple containing content and metadata
        """
        # Build paths
        metadata_file_path = self.metadata_path / metadata_subdir / f"{doc_id}-metadata.json"
        
        # Load metadata
        try:
            with open(metadata_file_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Metadata file not found: {metadata_file_path}")
            
        # Get content path from metadata
        if "FilePath" not in metadata:
            raise ValueError(f"FilePath not specified in metadata for {doc_id}")
            
        content_file_path = Path(metadata["FilePath"])
        
        # Load content
        try:
            with open(content_file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Content file not found: {content_file_path}")
            
        return content, metadata
    
    def _process_exam_content(
        self,
        question_paper_content: List[Dict],
        question_paper_metadata: Dict,
        mark_scheme_content: List[Dict],
        mark_scheme_metadata: Dict
    ) -> List[Dict]:
        """
        Process exam paper and mark scheme content to extract structured question data.
        
        Args:
            question_paper_content (List[Dict]): Question paper content
            question_paper_metadata (Dict): Question paper metadata
            mark_scheme_content (List[Dict]): Mark scheme content
            mark_scheme_metadata (Dict): Mark scheme metadata
            
        Returns:
            List[Dict]: List of parsed questions with mark schemes
        """
        # Implementation will go here
        pass
    
    def _extract_media_files(self, page_content: Dict) -> Dict[str, Dict]:
        """
        Extract media file information from page content.
        
        Args:
            page_content (Dict): Page content with potential image references
            
        Returns:
            Dict[str, Dict]: Dictionary of media files with their properties
        """
        # Implementation will go here
        pass
    
    def _add_media_file_references(self, parsed_questions: List[Dict], content: List[Dict]) -> None:
        """
        Add media file references to parsed questions.
        
        Args:
            parsed_questions (List[Dict]): Parsed questions
            content (List[Dict]): Original content with media information
        """
        # Implementation will go here
        pass
    
    def _update_index(self, parsed_questions: List[Dict], metadata: Dict) -> None:
        """
        Update the hierarchical index with processed question data.
        
        Args:
            parsed_questions (List[Dict]): Parsed questions
            metadata (Dict): Metadata for the exam paper
        """
        # Implementation will go here
        pass