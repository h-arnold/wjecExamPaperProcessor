#!/usr/bin/env python3
"""
Command-line interface for the ExamContentParser module.

This script provides a command-line interface for testing and running the
ExamContentParser, which processes WJEC exam papers and mark schemes to extract
structured question data.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dotenv import load_dotenv

# Set up workspace root path
WORKSPACE_ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
os.chdir(WORKSPACE_ROOT)

# Load environment variables from .env file
load_dotenv(WORKSPACE_ROOT / '.env')

# Import the ExamContentParser
try:
    from .exam_content_parser import ExamContentParser
    from ..Llm_client.mistral_client import MistralLLMClient
except ImportError:
    # When run directly as script
    sys.path.append(str(WORKSPACE_ROOT))
    from src.ExamContentParser.exam_content_parser import ExamContentParser
    from src.Llm_client.mistral_client import MistralLLMClient


def setup_logging(log_level: str) -> None:
    """
    Set up logging with the specified log level.
    
    Args:
        log_level (str): Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    """
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def find_first_valid_exam(index_data: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Find the first exam in the hierarchical index that has both a question paper and mark scheme.
    
    Args:
        index_data (Dict[str, Any]): Hierarchical index data
        
    Returns:
        Tuple[Optional[str], Optional[Dict[str, Any]]]: Exam identifier path and exam entry
    """
    for subject_name, subject in index_data.get('subjects', {}).items():
        for year, year_data in subject.get('years', {}).items():
            for qual_name, qualification in year_data.get('qualifications', {}).items():
                for exam_name, exam in qualification.get('exams', {}).items():
                    # Check if the exam has both question paper and mark scheme
                    documents = exam.get('documents', {})
                    question_papers = documents.get('Question Paper', [])
                    mark_schemes = documents.get('Mark Scheme', [])
                    
                    if question_papers and mark_schemes:
                        # Found a valid exam with both document types
                        exam_path = f"{subject_name} / {year} / {qual_name} / {exam_name}"
                        return exam_path, exam
    
    return None, None


def test_exam_parser(args: argparse.Namespace) -> int:
    """
    Test the ExamContentParser on the first valid exam in the hierarchical index.
    
    Args:
        args (argparse.Namespace): Command-line arguments
        
    Returns:
        int: Exit code (0 for success, non-zero for errors)
    """
    logger = logging.getLogger('exam_parser_test')
    logger.info("Starting exam parser test")
    
    # Load the hierarchical index
    try:
        with open(args.index, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        logger.info(f"Successfully loaded index from {args.index}")
    except Exception as e:
        logger.error(f"Failed to load index: {str(e)}")
        return 1
    
    # Find the first valid exam
    exam_path, exam = find_first_valid_exam(index_data)
    if not exam:
        logger.error("No valid exam found with both question paper and mark scheme")
        return 1
    
    logger.info(f"Found valid exam: {exam_path}")
    
    # Initialize the LLM client
    try:
        llm_client = MistralLLMClient(
            api_key=os.environ.get('MISTRAL_API_KEY'),
            model=args.model
        )
        logger.info(f"Initialized LLM client with model: {args.model}")
    except Exception as e:
        logger.error(f"Failed to initialize LLM client: {str(e)}")
        return 1
    
    # Initialize the ExamContentParser
    try:
        exam_parser = ExamContentParser(
            llm_client=llm_client,
            index_path=args.index,
            ocr_results_path=args.ocr_results,
            log_level=logging.getLevelName(args.log_level.upper())
        )
        logger.info("Initialized ExamContentParser")
    except Exception as e:
        logger.error(f"Failed to initialize ExamContentParser: {str(e)}")
        return 1
    
    # Process the exam
    try:
        success = exam_parser.process_exam_from_index(exam)
        if success:
            logger.info("Exam processing completed successfully")
            return 0
        else:
            logger.error("Exam processing failed")
            return 1
    except Exception as e:
        logger.error(f"Error during exam processing: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


def main() -> int:
    """
    Main function for the ExamContentParser command-line interface.
    
    Returns:
        int: Exit code (0 for success, non-zero for errors)
    """
    parser = argparse.ArgumentParser(
        description='WJEC Exam Paper Content Parser'
    )
    
    # Global arguments
    parser.add_argument(
        '--index',
        default='Index/hierarchical_index.json',
        help='Path to hierarchical index file (default: Index/hierarchical_index.json)'
    )
    parser.add_argument(
        '--ocr-results',
        default='ocr_results',
        help='Path to OCR results directory (default: ocr_results)'
    )
    parser.add_argument(
        '--output',
        default='Index/questions_index.json',
        help='Path for output questions index file (default: Index/questions_index.json)'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Set the logging level (default: INFO)'
    )
    parser.add_argument(
        '--model',
        default='mistral-medium',
        help='Mistral model to use for content parsing (default: mistral-medium)'
    )
    
    # Add subparsers for different commands
    subparsers = parser.add_subparsers(
        title='commands',
        dest='command',
        help='Command to execute',
        required=False  # Changed from True to False to allow default command
    )
    
    # Test command
    test_parser = subparsers.add_parser(
        'test',
        help='Test exam content parsing on the first valid exam'
    )
    test_parser.set_defaults(func=test_exam_parser)
    
    # Parse arguments and display help if no command is provided
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    
    # Default to test command if no command is specified
    if not args.command:
        args.command = 'test'
        args.func = test_exam_parser
    
    # Execute the appropriate function for the specified command
    try:
        return args.func(args)
    except Exception as e:
        logging.error(f"Command execution failed: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
