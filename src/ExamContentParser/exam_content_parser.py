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
        # Get starting indices from metadata
        qp_start_index = question_paper_metadata.get("QuestionStartIndex", 0)
        ms_start_index = mark_scheme_metadata.get("MarkSchemeStartIndex", 0)
        
        # Initialize current indices and question number
        current_qp_index = qp_start_index
        current_ms_index = ms_start_index
        current_question = 1
        
        # Store all parsed questions
        parsed_questions = []
        
        # Continue processing until we reach the end of either document
        while (current_qp_index < len(question_paper_content) and 
               current_ms_index < len(mark_scheme_content)):
            
            self.logger.info(f"Processing window at QP index: {current_qp_index}, MS index: {current_ms_index}, Question: {current_question}")
            
            # Create window parameters for the parser
            content_window = self._create_content_window(
                question_paper_content,
                mark_scheme_content,
                current_qp_index,
                current_ms_index,
                current_question
            )
            
            # Create parser with the content window
            parser = QuestionAndMarkschemeParser(content_window)
            
            # Send to LLM client for processing
            try:
                # Use generate_text instead of generate_from_prompt
                # Access the prompt using the correct attribute name
                response = self.llm_client.generate_json(parser._prompt)
                parsed_response = self._parse_llm_response(response)
                
                # Add parsed questions to our collection
                if "questions" in parsed_response:
                    parsed_questions.extend(parsed_response["questions"])
                
                # Update indices for next iteration based on parser response
                next_qp_index = parsed_response.get("next_question_paper_index")
                next_ms_index = parsed_response.get("next_mark_scheme_index")
                next_question = parsed_response.get("next_question_number")
                
                # Check if we have valid next indices
                if next_qp_index is None or next_ms_index is None:
                    self.logger.warning("Parser did not return next indices, stopping processing")
                    break
                
                # Update current indices and question number for next iteration
                current_qp_index = next_qp_index
                current_ms_index = next_ms_index
                if next_question is not None:
                    current_question = next_question
                else:
                    # If no next question number provided, increment by number of questions parsed
                    current_question += len(parsed_response.get("questions", []))
                
            except Exception as e:
                self.logger.error(f"Error processing content window: {str(e)}", exc_info=True)
                # We could implement retry logic here if needed
                break
        
        self.logger.info(f"Completed processing with {len(parsed_questions)} questions parsed")
        return parsed_questions
    
    def _create_content_window(
        self,
        question_paper_content: List[Dict], 
        mark_scheme_content: List[Dict],
        qp_current_index: int,
        ms_current_index: int,
        current_question: int,
        window_size: int = 2
    ) -> Dict[str, Any]:
        """
        Create a window of content for processing by the LLM.
        
        Args:
            question_paper_content: Full question paper content
            mark_scheme_content: Full mark scheme content
            qp_current_index: Current index in question paper
            ms_current_index: Current index in mark scheme
            current_question: Current question number
            window_size: Maximum number of pages to include in window (default: 2)
            
        Returns:
            Dict: Parameters for the QuestionAndMarkschemeParser
            
        Note:
            The window_size parameter controls the maximum potential window size,
            but actual content provided to the parser is determined by the available
            pages in the content.
        """
        # Create parameters dictionary for QuestionAndMarkschemeParser
        window_params = {
            "question_paper_content": question_paper_content,
            "mark_scheme_content": mark_scheme_content,
            "question_start_index": qp_current_index,
            "mark_scheme_start_index": ms_current_index,
            "current_question_number": current_question,
            "current_question_paper_index": qp_current_index,
            "current_mark_scheme_index": ms_current_index
        }
        
        # Log the window creation
        total_qp_pages = len(question_paper_content)
        total_ms_pages = len(mark_scheme_content)
        
        # Calculate remaining pages for logging
        qp_remaining = max(0, total_qp_pages - qp_current_index)
        ms_remaining = max(0, total_ms_pages - ms_current_index)
        
        self.logger.debug(
            f"Creating content window: Question {current_question}, "
            f"QP index {qp_current_index}/{total_qp_pages-1} ({qp_remaining} pages remaining), "
            f"MS index {ms_current_index}/{total_ms_pages-1} ({ms_remaining} pages remaining)"
        )
        
        return window_params
    
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

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Parse and extract structured data from LLM response.
        
        Args:
            response (str): Raw response from LLM
            
        Returns:
            Dict[str, Any]: Structured data including parsed questions and next indices
            
        Raises:
            ValueError: If response cannot be parsed or is missing required fields
        """
        # Try to find and extract JSON from response
        try:
            # Look for JSON in the response (which might have non-JSON content as well)
            json_pattern = r'```json\s*([\s\S]*?)\s*```'
            json_matches = re.findall(json_pattern, response)
            
            # If we found JSON blocks, use the first one
            if json_matches:
                json_str = json_matches[0]
                structured_data = json.loads(json_str)
                
            else:
                # Try to parse the entire response as JSON
                json_str = response.strip()
                structured_data = json.loads(json_str)
                
        except (json.JSONDecodeError, IndexError) as e:
            self.logger.error(f"Failed to parse LLM response as JSON: {str(e)}")
            self.logger.debug(f"Problematic response: {response[:200]}...")  # Log just the start for debugging
            raise ValueError(f"Could not extract valid JSON from LLM response: {str(e)}")
            
        # Validate required fields
        required_fields = ["next_question_paper_index", "next_mark_scheme_index"]
        missing_fields = [field for field in required_fields if field not in structured_data]
        
        if missing_fields:
            self.logger.warning(f"LLM response missing required fields: {missing_fields}")
            
            # If no valid indices provided, we need to stop processing
            if "next_question_paper_index" in missing_fields or "next_mark_scheme_index" in missing_fields:
                raise ValueError(f"LLM response missing critical navigation fields: {missing_fields}")
        
        # Validate questions field if present
        if "questions" in structured_data:
            if not isinstance(structured_data["questions"], list):
                self.logger.warning("Questions field is not a list, converting to list")
                # If questions is a single item, wrap it in a list
                structured_data["questions"] = [structured_data["questions"]]
                
            # Ensure each question has required fields
            for i, question in enumerate(structured_data["questions"]):
                if not isinstance(question, dict):
                    self.logger.warning(f"Question {i} is not a dictionary, skipping")
                    continue
                    
                question_required = ["question_number", "question_text"]
                question_missing = [field for field in question_required if field not in question]
                
                if question_missing:
                    self.logger.warning(f"Question {i} missing fields: {question_missing}")
                    # Add placeholder values for missing fields
                    for field in question_missing:
                        question[field] = f"MISSING_{field}_PLACEHOLDER"
        else:
            self.logger.warning("No questions found in LLM response")
            structured_data["questions"] = []
            
        return structured_data

    def process_exam_from_index(self, exam_entry: Dict[str, Any]) -> bool:
        """
        Process an exam directly from a hierarchical index entry.
        
        This method extracts question paper and mark scheme IDs from the exam entry
        in the hierarchical index and processes them.
        
        Args:
            exam_entry (Dict[str, Any]): Exam entry from the hierarchical index
            
        Returns:
            bool: True if processing was successful, False otherwise
            
        Raises:
            ValueError: If required documents are not found in the exam entry
        """
        # Check if the exam entry has the required document types
        if "documents" not in exam_entry:
            raise ValueError("Exam entry does not contain documents section")
            
        documents = exam_entry["documents"]
        question_papers = documents.get("Question Paper", [])
        mark_schemes = documents.get("Mark Scheme", [])
        
        # Check if we have both question paper and mark scheme
        if not question_papers:
            raise ValueError("No Question Paper found in exam entry")
        if not mark_schemes:
            raise ValueError("No Mark Scheme found in exam entry")
            
        # For now, just use the first question paper and mark scheme
        # In the future, we could implement more sophisticated matching
        question_paper = question_papers[0]
        mark_scheme = mark_schemes[0]
        
        # Extract document IDs
        qp_id = question_paper.get("id")
        ms_id = mark_scheme.get("id")
        
        if not qp_id or not ms_id:
            raise ValueError("Document IDs not found in exam entry")
            
        self.logger.info(f"Processing exam with QP ID: {qp_id}, MS ID: {ms_id}")
        
        # Process the exam content
        return self.parse_exam_content(qp_id, ms_id)