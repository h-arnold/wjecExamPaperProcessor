"""
ExamContentParser - Module for parsing exam paper and mark scheme content.

This module processes OCR results from exam papers and mark schemes, extracts
structured question and mark scheme data using an LLM, and updates the hierarchical
index with the processed content including references to media files.
"""

import json
import logging
import re
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

# Import related modules
from ..Prompts.question_and_markscheme_parser import QuestionAndMarkschemeParser
from ..Llm_client.base_client import LLMClient
from ..Llm_client.factory import LLMClientFactory


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
        llm_client: LLMClient = None,
        index_path: Union[str, Path] = None,
        ocr_results_path: Union[str, Path] = None,
        metadata_path: Union[str, Path] = None,
        llm_provider: str = "mistral",
        log_level: int = logging.INFO,
        **llm_options
    ):
        """
        Initialize the ExamContentParser.
        
        Args:
            llm_client (LLMClient, optional): Client for interacting with the LLM API
            index_path (Union[str, Path], optional): Path to the hierarchical index JSON file
            ocr_results_path (Union[str, Path], optional): Path to the directory containing OCR results
            metadata_path (Union[str, Path], optional): Path to the directory containing metadata
            llm_provider (str, optional): LLM provider to use if no client is provided. Default is 'mistral'
            log_level (int, optional): Logging level (default: logging.INFO)
            **llm_options: Additional options to pass to the LLM client if created
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
        
        # Initialize LLM client if not provided
        if llm_client is None:
            factory = LLMClientFactory()
            self.llm_client = factory.create_client(llm_provider, **llm_options)
            self.logger.info(f"Created new LLM client for {llm_provider}")
        else:
            self.llm_client = llm_client
            
        # Store paths
        if index_path:
            self.index_path = Path(index_path)
            # Validate index path
            if not self.index_path.exists():
                raise FileNotFoundError(f"Index file not found at: {self.index_path}")
        else:
            self.index_path = None
            
        if ocr_results_path:
            self.ocr_results_path = Path(ocr_results_path)
            # Validate OCR results path
            if not self.ocr_results_path.exists():
                raise FileNotFoundError(f"OCR results directory not found at: {self.ocr_results_path}")
        else:
            self.ocr_results_path = None

        if metadata_path:
            self.metadata_path = Path(metadata_path)
            # Validate metadata path
            if not self.metadata_path.exists():
                raise FileNotFoundError(f"Metadata directory not found at: {self.metadata_path}")
        else:
            self.metadata_path = None

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
            # Check if index path is set
            if not self.index_path:
                raise ValueError("Index path not set. Provide a valid index_path during initialization.")
                
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
    
    def _load_exam_content_and_metadata(self, file_id: str, content_type: str) -> (List[Dict], Dict):
        """
        Load exam content and its metadata for a given file ID and content type.
        
        Args:
            file_id (str): Identifier of the file (without extension)
            content_type (str): Subdirectory name for content and metadata (e.g., 'question_papers')
        Returns:
            Tuple[List[Dict], Dict]: Content list and metadata dict
        Raises:
            FileNotFoundError: If either file cannot be found
        """
        # Construct paths
        metadata_file = self.metadata_path / content_type / f"{file_id}.json"
        content_file = self.ocr_results_path / content_type / f"{file_id}.json"
        # Load metadata
        try:
            with open(metadata_file, 'r', encoding='utf-8') as mf:
                metadata = json.load(mf)
        except FileNotFoundError:
            raise FileNotFoundError(f"Metadata file not found: {metadata_file}")
        # Load content
        try:
            with open(content_file, 'r', encoding='utf-8') as cf:
                content = json.load(cf)
        except FileNotFoundError:
            raise FileNotFoundError(f"Content file not found: {content_file}")
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
        
        # Track context window expansion attempts to prevent infinite loops
        context_expansion_attempts = 0
        max_context_expansions = 3  # Limit to prevent endless expansion
        
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
            
            try:
                # Use generate_json which already returns a dictionary
                response = self.llm_client.generate_json(parser._prompt)
                parsed_response = self._parse_llm_response(response, current_qp_index, current_ms_index)
                
                # Check if we need more context
                context_complete = parsed_response.get("context_complete", {"question_paper": True, "mark_scheme": True})
                needs_more_qp = not context_complete.get("question_paper", True)
                needs_more_ms = not context_complete.get("mark_scheme", True)
                
                if (needs_more_qp or needs_more_ms) and context_expansion_attempts < max_context_expansions:
                    # Expand context window and retry
                    context_expansion_attempts += 1
                    self.logger.info(f"Expanding context window (attempt {context_expansion_attempts}/{max_context_expansions})")
                    
                    # Increment indices for areas that need more context
                    if needs_more_qp:
                        current_qp_index += 1
                        self.logger.info(f"Expanding question paper context to index {current_qp_index}")
                    
                    if needs_more_ms:
                        current_ms_index += 1
                        self.logger.info(f"Expanding mark scheme context to index {current_ms_index}")
                    
                    # Skip to the next iteration to retry with expanded context
                    continue
                
                # Reset expansion counter if we've successfully processed content
                context_expansion_attempts = 0
                
                # Add parsed questions to our collection
                if "questions" in parsed_response and parsed_response["questions"]:
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
        media_files = {}
        
        # Check if the page has images
        if 'images' in page_content and page_content['images']:
            for image in page_content['images']:
                # Extract image ID and path
                image_id = image.get('id')
                if not image_id:
                    continue
                    
                # Create media file entry with all properties
                media_files[image_id] = {
                    'id': image_id,
                    'path': image.get('image_path'),
                    'coordinates': {
                        'top_left_x': image.get('top_left_x'),
                        'top_left_y': image.get('top_left_y'),
                        'bottom_right_x': image.get('bottom_right_x'),
                        'bottom_right_y': image.get('bottom_right_y')
                    },
                    'page_index': page_content.get('index')
                }
            
        return media_files
    
    def _add_media_file_references(self, parsed_questions: List[Dict], content: List[Dict]) -> None:
        """
        Add media file references to parsed questions.
        
        Args:
            parsed_questions (List[Dict]): Parsed questions
            content (List[Dict]): Original content with media information
        """
        # First, extract all media files from all pages
        all_media = {}
        for page in content:
            page_media = self._extract_media_files(page)
            all_media.update(page_media)
            
        if not all_media:
            self.logger.info("No media files found in content")
            return
            
        self.logger.info(f"Found {len(all_media)} media files in content")
        
        # Process each question to find references to media files
        for question in parsed_questions:
            # Initialize media_files array if not present
            if 'media_files' not in question:
                question['media_files'] = []
                
            # Check if question text contains image references
            question_text = question.get('question_text', '')
            
            # Look for markdown image references: ![alt text](image_id)
            image_references = re.findall(r'!\[.*?\]\((.*?)\)', question_text)
            
            # Add unique media files referenced in this question
            for ref in image_references:
                # Extract the image ID from the reference
                # The reference might be just the ID or include file extension
                image_id = ref.split('/')[-1]  # Handle paths like folder/img.jpeg
                base_ref = image_id
                
                # Check if the reference exists in our media dictionary
                if base_ref in all_media:
                    media_info = all_media[base_ref]
                    
                    # Add if not already added (checking by ID)
                    if not any(m.get('id') == media_info['id'] for m in question['media_files']):
                        question['media_files'].append({
                            'id': media_info['id'],
                            'path': media_info['path'],
                            'coordinates': media_info['coordinates'],
                            'page_index': media_info['page_index']
                        })
                        self.logger.debug(f"Added media file {media_info['id']} to question {question.get('question_number')}")
            
            # Process sub-questions recursively if they exist
            if 'sub_questions' in question and question['sub_questions']:
                self._add_media_file_references(question['sub_questions'], content)
    
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
        if not document_id or not document_record:
            raise ValueError("Document ID and document record are required to update the index")
            
        self.logger.info(f"Updating hierarchical index for document {document_id}")
        
        try:
            # Load the hierarchical index
            with open(self.index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            # Find the correct document record in the hierarchical index
            document_updated = False
            
            # Traverse the index to find and update the document record
            for subject_name, subject in index_data.get('subjects', {}).items():
                for year, year_data in subject.get('years', {}).items():
                    for qual_name, qualification in year_data.get('qualifications', {}).items():
                        for exam_name, exam in qualification.get('exams', {}).items():
                            for doc_type, documents in exam.get('documents', {}).items():
                                for doc_idx, doc in enumerate(documents):
                                    if doc.get('id') == document_id:
                                        # Found the document record to update
                                        self.logger.info(f"Found document record for {document_id} in {subject_name}, {year}, {qual_name}, {exam_name}")
                                        
                                        # Add parsed questions to the document record
                                        doc['questions'] = parsed_questions
                                        
                                        # Add timestamp to track when the document was processed
                                        doc['processed_at'] = datetime.datetime.now().isoformat()
                                        
                                        document_updated = True
                                        break
                                
                                if document_updated:
                                    break
                            if document_updated:
                                break
                        if document_updated:
                            break
                    if document_updated:
                        break
                if document_updated:
                    break
            
            if not document_updated:
                self.logger.warning(f"Could not find document record for {document_id} in the index")
            
            # Save the updated index to a new file for development purposes
            # Always save the file, even if the document wasn't found
            output_path = Path(self.index_path).parent / "final_index.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2)
            
            self.logger.info(f"Updated hierarchical index saved to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error updating index: {str(e)}", exc_info=True)
            raise

    def _parse_llm_response(self, response: Dict[str, Any], current_qp_index: int = None, current_ms_index: int = None) -> Dict[str, Any]:
        """
        Process and validate structured data from LLM response.
        
        Args:
            response (Dict[str, Any]): Parsed response from LLM as a dictionary
            current_qp_index (int, optional): Current question paper index, used for fallback
            current_ms_index (int, optional): Current mark scheme index, used for fallback
            
        Returns:
            Dict[str, Any]: Validated data including parsed questions and next indices
            
        Raises:
            ValueError: If response is missing required fields
        """
        # Store original response for logging purposes
        original_response = response
        
        # Handle raw string responses by extracting and parsing JSON
        if isinstance(response, str):
            # Extract JSON block if present
            json_block = None
            match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
            if match:
                json_block = match.group(1)
            else:
                json_block = response
            try:
                structured_data = json.loads(json_block)
            except Exception as e:
                # Log the failed response
                self.logger.error(f"Failed to parse JSON from LLM response: {str(e)}")
                self.logger.error(f"Raw response: {original_response}")
                raise ValueError("Invalid JSON in LLM response")
        else:
            structured_data = response

        # Initialize context completion flags if not present
        if "context_complete" not in structured_data:
            structured_data["context_complete"] = {
                "question_paper": True,  # Default to true
                "mark_scheme": True
            }
        elif not isinstance(structured_data["context_complete"], dict):
            structured_data["context_complete"] = {
                "question_paper": bool(structured_data["context_complete"]),
                "mark_scheme": bool(structured_data["context_complete"])
            }
            
        # Validate required fields
        required_fields = ["next_question_paper_index", "next_mark_scheme_index"]
        missing_fields = [field for field in required_fields if field not in structured_data]
        
        if missing_fields:
            self.logger.warning(f"LLM response missing required fields: {missing_fields}")
            self.logger.warning(f"Full response structure: {json.dumps(structured_data, indent=2)}")
            
            # Use context completion flags to determine next indices
            if "next_question_paper_index" in missing_fields:
                needs_more_context = not structured_data["context_complete"]["question_paper"]
                if needs_more_context and current_qp_index is not None:
                    structured_data["next_question_paper_index"] = current_qp_index + 1
                    self.logger.info("Incrementing question paper index for more context")
                elif current_qp_index is not None and structured_data.get("questions"):
                    # Advance by one when current index is known
                    structured_data["next_question_paper_index"] = current_qp_index + 1
                    self.logger.info("Advancing question paper index by default")
                else:
                    self.logger.error(f"Cannot determine next_question_paper_index. Original response: {original_response}")
                    raise ValueError("Cannot determine next_question_paper_index")
                    
            if "next_mark_scheme_index" in missing_fields:
                needs_more_context = not structured_data["context_complete"]["mark_scheme"]
                if needs_more_context and current_ms_index is not None:
                    structured_data["next_mark_scheme_index"] = current_ms_index + 1
                    self.logger.info("Incrementing mark scheme index for more context")
                elif current_ms_index is not None and structured_data.get("questions"):
                    # Advance by one when current index is known
                    structured_data["next_mark_scheme_index"] = current_ms_index + 1
                    self.logger.info("Advancing mark scheme index by default")
                else:
                    self.logger.error(f"Cannot determine next_mark_scheme_index. Original response: {original_response}")
                    raise ValueError("Cannot determine next_mark_scheme_index")
        
        # Validate questions field if present
        if "questions" in structured_data:
            if not isinstance(structured_data["questions"], list):
                self.logger.warning("Questions field is not a list, converting to list")
                self.logger.debug(f"Original questions data: {structured_data['questions']}")
                # If questions is a single item, wrap it in a list
                structured_data["questions"] = [structured_data["questions"]]
                
            # Process and validate each question
            validated_questions = []
            for i, question in enumerate(structured_data["questions"]):
                # Validate required question fields
                required_question_fields = ["question_number", "question_text", "mark_scheme", "max_marks"]
                missing_question_fields = [field for field in required_question_fields if field not in question]
                
                if missing_question_fields:
                    self.logger.warning(f"Question {i} missing required fields: {missing_question_fields}")
                    self.logger.warning(f"Question data: {json.dumps(question, indent=2)}")
                    # Add any missing fields with default values
                    for field in missing_question_fields:
                        if field == "max_marks":
                            question[field] = 0
                        elif field == "assessment_objectives":
                            question[field] = []
                        else:
                            question[field] = ""
                
                # Ensure assessment_objectives is a list
                if "assessment_objectives" in question and not isinstance(question["assessment_objectives"], list):
                    question["assessment_objectives"] = [question["assessment_objectives"]]
                
                # Process sub-questions recursively if present
                if "sub_questions" in question and question["sub_questions"]:
                    if not isinstance(question["sub_questions"], list):
                        question["sub_questions"] = [question["sub_questions"]]
                        
                validated_questions.append(question)
                
            # Replace with validated questions
            structured_data["questions"] = validated_questions
        else:
            # Initialize empty questions list if not present
            structured_data["questions"] = []
            self.logger.warning("No questions found in LLM response")
            self.logger.debug(f"Full response: {json.dumps(structured_data, indent=2)}")
        
        # Add validation flags
        is_valid = len(missing_fields) == 0 and len(structured_data["questions"]) > 0
        structured_data["is_valid"] = is_valid
        
        if not is_valid:
            # Log the entire response if validation failed
            self.logger.warning("LLM response validation failed")
            self.logger.debug(f"Full original response: {original_response}")
            self.logger.debug(f"Processed response structure: {json.dumps(structured_data, indent=2)}")
        
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