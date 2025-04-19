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
        log_level: int = logging.INFO
    ):
        """
        Initialize the ExamContentParser.
        
        Args:
            llm_client (MistralLLMClient): Client for interacting with the Mistral LLM API
            index_path (Union[str, Path]): Path to the hierarchical index JSON file
            ocr_results_path (Union[str, Path]): Path to the directory containing OCR resultsd
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
        
        # Validate paths
        if not self.index_path.exists():
            raise FileNotFoundError(f"Index file not found at: {self.index_path}")
        if not self.ocr_results_path.exists():
            raise FileNotFoundError(f"OCR results directory not found at: {self.ocr_results_path}")
            
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
            # Load the hierarchical index
            with open(self.index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            # Initialize path variables
            qp_content_path = None
            ms_content_path = None
            qp_start_index = 0
            ms_start_index = 0
            
            # Find the document records in the hierarchical index
            qp_record = self._find_document_in_index(index_data, question_paper_id, "Question Paper")
            ms_record = self._find_document_in_index(index_data, mark_scheme_id, "Mark Scheme")
            
            # Extract paths and start indices from the records if found
            if qp_record:
                qp_content_path = qp_record.get('content_path')
                qp_start_index = qp_record.get('question_start_index', 0)
                
            if ms_record:
                ms_content_path = ms_record.get('content_path')
                ms_start_index = ms_record.get('question_start_index', 0)
            
            if not qp_content_path or not ms_content_path:
                raise ValueError(f"Could not find content paths for documents: {question_paper_id}, {mark_scheme_id}")
                
            self.logger.info(f"Loading content for paper {question_paper_id} and mark scheme {mark_scheme_id}")
            
            # 1. Load question paper and mark scheme content
            qp_content = self._load_exam_content(qp_content_path)
            ms_content = self._load_exam_content(ms_content_path)
            
            # 2. Process content to extract questions and mark scheme data using start indices from index
            qp_metadata = {'QuestionStartIndex': qp_start_index}
            ms_metadata = {'MarkSchemeStartIndex': ms_start_index}
            parsed_questions = self._process_exam_content(
                qp_content, qp_metadata, ms_content, ms_metadata)
            
            # 3. Add media file references
            self._add_media_file_references(parsed_questions, qp_content)
            
            # 4. Update the hierarchical index - also pass document ID and document record
            self._update_index(parsed_questions, qp_metadata, 
                              document_id=question_paper_id, document_record=qp_record)
            
            self.logger.info(f"Successfully processed exam paper {question_paper_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing exam content: {str(e)}", exc_info=True)
            return False
    
    def _find_document_in_index(self, index_data: Dict, document_id: str, document_type: str) -> Optional[Dict]:
        """
        Find a document record in the hierarchical index by ID and type.
        
        Args:
            index_data (Dict): The hierarchical index data
            document_id (str): The document ID to find
            document_type (str): The type of document ("Question Paper" or "Mark Scheme")
            
        Returns:
            Optional[Dict]: The document record if found, None otherwise
        """
        for subject_name, subject in index_data.get('subjects', {}).items():
            for year, year_data in subject.get('years', {}).items():
                for qual_name, qualification in year_data.get('qualifications', {}).items():
                    for exam_name, exam in qualification.get('exams', {}).items():
                        if document_type in exam.get('documents', {}):
                            for doc in exam.get('documents', {}).get(document_type, []):
                                if doc.get('id') == document_id:
                                    return doc
        return None
    
    def _load_exam_content(self, content_path: str) -> List[Dict]:
        """
        Load exam content from a file.
        
        Args:
            content_path (str): Path to the content file
            
        Returns:
            List[Dict]: The loaded content
            
        Raises:
            FileNotFoundError: If the content file cannot be found
        """
        content_file_path = Path(content_path)
        
        # Load content
        try:
            with open(content_file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Content file not found: {content_file_path}")
            
        return content
    
    
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
            question_paper_metadata (Dict): Question paper metadata (with QuestionStartIndex)
            mark_scheme_content (List[Dict]): Mark scheme content
            mark_scheme_metadata (Dict): Mark scheme metadata (with MarkSchemeStartIndex)
            
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
                parsed_response = self._parse_llm_response(response, current_qp_index, current_ms_index)
                
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
    
    def _update_index(
        self, 
        parsed_questions: List[Dict], 
        metadata: Dict, 
        document_id: str = None,
        document_record: Dict = None
    ) -> None:
        """
        Update the hierarchical index with processed question data.
        
        Args:
            parsed_questions (List[Dict]): Parsed questions
            metadata (Dict): Basic metadata for the exam paper
            document_id (str, optional): ID of the document being processed
            document_record (Dict, optional): Original document record from the index
        """
        # Implementation will go here
        pass

    def _parse_llm_response(self, response: str, current_qp_index: int = None, current_ms_index: int = None) -> Dict[str, Any]:
        """
        Parse and extract structured data from LLM response.
        
        Args:
            response (str): Raw response from LLM
            current_qp_index (int, optional): Current question paper index, used for fallback
            current_ms_index (int, optional): Current mark scheme index, used for fallback
            
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
            
            # Try fallback extraction (look for anything that might be JSON)
            try:
                # Look for content that looks like JSON (starts with { and ends with })
                fallback_pattern = r'(\{[\s\S]*\})'
                fallback_matches = re.findall(fallback_pattern, response)
                
                if fallback_matches:
                    for potential_json in fallback_matches:
                        try:
                            structured_data = json.loads(potential_json)
                            self.logger.warning("Used fallback JSON extraction")
                            break
                        except json.JSONDecodeError:
                            continue
                    else:  # No valid JSON found in fallback matches
                        raise ValueError("No valid JSON found in fallback extraction")
                else:
                    raise ValueError("No JSON-like content found in response")
            except Exception as fallback_error:
                raise ValueError(f"Could not extract valid JSON from LLM response: {str(e)}\nFallback extraction failed: {str(fallback_error)}")
            
        # Validate required fields
        required_fields = ["next_question_paper_index", "next_mark_scheme_index"]
        missing_fields = [field for field in required_fields if field not in structured_data]
        
        if missing_fields:
            self.logger.warning(f"LLM response missing required fields: {missing_fields}")
            
            # Try to infer missing navigation fields if possible
            if "next_question_paper_index" in missing_fields:
                if current_qp_index is not None and "questions" in structured_data and structured_data["questions"]:
                    # Assume we need to advance one page if processing was successful
                    self.logger.warning("Inferring next_question_paper_index")
                    structured_data["next_question_paper_index"] = current_qp_index + 1
                else:
                    raise ValueError("Cannot infer next_question_paper_index")
                    
            if "next_mark_scheme_index" in missing_fields:
                if current_ms_index is not None and "questions" in structured_data and structured_data["questions"]:
                    # Assume we need to advance one page if processing was successful
                    self.logger.warning("Inferring next_mark_scheme_index")
                    structured_data["next_mark_scheme_index"] = current_ms_index + 1
                else:
                    raise ValueError("Cannot infer next_mark_scheme_index")
        
        # Validate questions field if present
        if "questions" in structured_data:
            if not isinstance(structured_data["questions"], list):
                self.logger.warning("Questions field is not a list, converting to list")
                # If questions is a single item, wrap it in a list
                structured_data["questions"] = [structured_data["questions"]]
                
            # Process and validate each question
            validated_questions = []
            for i, question in enumerate(structured_data["questions"]):
                if not isinstance(question, dict):
                    self.logger.warning(f"Question {i} is not a dictionary, skipping")
                    continue
                    
                # Required question fields
                question_required = ["question_number", "question_text", "mark_scheme"]
                question_missing = [field for field in question_required if field not in question]
                
                if question_missing:
                    self.logger.warning(f"Question {i} missing fields: {question_missing}")
                    # Add placeholder values for missing fields
                    for field in question_missing:
                        if field == "question_text":
                            question[field] = "Missing question text"
                        elif field == "mark_scheme":
                            question[field] = "Missing mark scheme"
                        elif field == "question_number":
                            # Try to infer question number from context
                            if i > 0 and "question_number" in validated_questions[-1]:
                                prev_number = validated_questions[-1]["question_number"]
                                # Try to increment the number based on common patterns
                                if re.match(r'^\d+$', prev_number):  # Simple number like "1"
                                    question[field] = str(int(prev_number) + 1)
                                elif re.match(r'^\d+[a-z]$', prev_number):  # Like "1a"
                                    base = prev_number[:-1]
                                    suffix = chr(ord(prev_number[-1]) + 1)
                                    question[field] = f"{base}{suffix}"
                                else:
                                    question[field] = f"Unknown_{i}"
                            else:
                                question[field] = f"Unknown_{i}"
                            
                            self.logger.warning(f"Inferred question_number: {question[field]}")
                
                # Optional fields with defaults
                if "max_marks" not in question:
                    # Try to extract marks from question text
                    marks_pattern = r'\[(\d+)\s*(?:marks|mark)\]'
                    marks_match = re.search(marks_pattern, question.get("question_text", ""), re.IGNORECASE)
                    if marks_match:
                        question["max_marks"] = int(marks_match.group(1))
                        self.logger.debug(f"Extracted max_marks={question['max_marks']} from question text")
                    else:
                        question["max_marks"] = 0  # Default if not found
                        
                if "assessment_objectives" not in question:
                    # Try to extract AO references from mark scheme
                    ao_pattern = r'AO(\d+)'
                    ao_matches = re.findall(ao_pattern, question.get("mark_scheme", ""))
                    if ao_matches:
                        question["assessment_objectives"] = [f"AO{ao}" for ao in set(ao_matches)]
                        self.logger.debug(f"Extracted assessment_objectives={question['assessment_objectives']} from mark scheme")
                    else:
                        question["assessment_objectives"] = []  # Default if not found
                
                # Check for sub-questions
                if "sub_questions" in question and question["sub_questions"]:
                    # Recursively validate sub-questions using the same logic
                    if not isinstance(question["sub_questions"], list):
                        question["sub_questions"] = [question["sub_questions"]]
                    
                    validated_sub_questions = []
                    for j, sub_q in enumerate(question["sub_questions"]):
                        if not isinstance(sub_q, dict):
                            continue
                            
                        # Validate required fields for sub-question
                        for req_field in question_required:
                            if req_field not in sub_q:
                                if req_field == "question_number":
                                    # Infer from parent question
                                    parent_num = question.get("question_number", f"Unknown_{i}")
                                    sub_q[req_field] = f"{parent_num}.{j+1}"
                                else:
                                    sub_q[req_field] = f"Missing {req_field}"
                        
                        # Add optional fields with defaults for sub-question
                        if "max_marks" not in sub_q:
                            marks_match = re.search(r'\[(\d+)\s*(?:marks|mark)\]', sub_q.get("question_text", ""), re.IGNORECASE)
                            sub_q["max_marks"] = int(marks_match.group(1)) if marks_match else 0
                            
                        if "assessment_objectives" not in sub_q:
                            ao_matches = re.findall(r'AO(\d+)', sub_q.get("mark_scheme", ""))
                            sub_q["assessment_objectives"] = [f"AO{ao}"] if ao_matches else []
                            
                        validated_sub_questions.append(sub_q)
                    
                    question["sub_questions"] = validated_sub_questions
                
                # Check for incomplete questions (spanning multiple windows)
                incomplete_markers = ["...", "continues", "continued", "incomplete"]
                is_incomplete = any(marker in question.get("question_text", "").lower() for marker in incomplete_markers)
                if is_incomplete:
                    question["is_incomplete"] = True
                    self.logger.warning(f"Question {question.get('question_number', i)} appears to be incomplete")
                
                validated_questions.append(question)
            
            # Replace original questions with validated ones
            structured_data["questions"] = validated_questions
        else:
            self.logger.warning("No questions found in LLM response")
            structured_data["questions"] = []
        
        # Add validation flags
        structured_data["is_valid"] = len(missing_fields) == 0 and len(structured_data["questions"]) > 0
        
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