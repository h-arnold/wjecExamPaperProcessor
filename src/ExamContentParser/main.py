#!/usr/bin/env python3
"""
Command-line interface for the ExamContentParser module.

This script provides a command-line interface for processing WJEC exam papers 
and mark schemes to extract structured question data.
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime
from tqdm import tqdm
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


def setupLogging(logLevel: str, outputDir: Optional[str] = None) -> logging.Logger:
    """
    Set up logging with the specified log level.
    
    Args:
        logLevel (str): Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        outputDir (str, optional): Directory where log files should be saved
        
    Returns:
        logging.Logger: Configured logger instance
    """
    numericLevel = getattr(logging, logLevel.upper(), None)
    if not isinstance(numericLevel, int):
        raise ValueError(f"Invalid log level: {logLevel}")
    
    # Create logger
    logger = logging.getLogger('exam_content_parser')
    logger.setLevel(numericLevel)
    
    # Create console handler
    consoleHandler = logging.StreamHandler()
    consoleHandler.setLevel(numericLevel)
    consoleFormatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    consoleHandler.setFormatter(consoleFormatter)
    logger.addHandler(consoleHandler)
    
    # Create file handler if output directory is provided
    if outputDir:
        outputPath = Path(outputDir)
        outputPath.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        logFile = outputPath / f"exam_content_parser_{timestamp}.log"
        
        fileHandler = logging.FileHandler(logFile)
        fileHandler.setLevel(numericLevel)
        fileFormatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fileHandler.setFormatter(fileFormatter)
        logger.addHandler(fileHandler)
        
        logger.info(f"Logging to file: {logFile}")
    
    return logger


def loadHierarchicalIndex(indexPath: Union[str, Path]) -> Dict[str, Any]:
    """
    Load the hierarchical index from the specified path.
    
    Args:
        indexPath (Union[str, Path]): Path to the hierarchical index file
        
    Returns:
        Dict[str, Any]: Loaded index data
        
    Raises:
        FileNotFoundError: If the index file does not exist
        json.JSONDecodeError: If the index file contains invalid JSON
    """
    indexPath = Path(indexPath)
    if not indexPath.exists():
        raise FileNotFoundError(f"Index file not found: {indexPath}")
    
    with open(indexPath, 'r', encoding='utf-8') as f:
        try:
            indexData = json.load(f)
            return indexData
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON in index file: {e.msg}", e.doc, e.pos)


def findAllExams(indexData: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Find all exams in the index that have both question papers and mark schemes.
    
    Args:
        indexData (Dict[str, Any]): Hierarchical index data
        
    Returns:
        List[Tuple[str, Dict[str, Any]]]: List of (exam path, exam data) pairs
    """
    validExams = []
    
    for subjectName, subject in indexData.get('subjects', {}).items():
        for year, yearData in subject.get('years', {}).items():
            for qualName, qualification in yearData.get('qualifications', {}).items():
                for examName, exam in qualification.get('exams', {}).items():
                    # Check if the exam has both question paper and mark scheme
                    documents = exam.get('documents', {})
                    questionPapers = documents.get('Question Paper', [])
                    markSchemes = documents.get('Mark Scheme', [])
                    
                    if questionPapers and markSchemes:
                        examPath = f"{subjectName} / {year} / {qualName} / {examName}"
                        validExams.append((examPath, exam))
    
    return validExams


def filterExamsByCriteria(
    allExams: List[Tuple[str, Dict[str, Any]]], 
    subject: Optional[str] = None,
    year: Optional[int] = None, 
    qualification: Optional[str] = None,
    unit: Optional[int] = None,
    processed: Optional[bool] = None
) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Filter exams based on specified criteria.
    
    Args:
        allExams: List of (exam path, exam data) pairs
        subject: Subject name filter
        year: Year filter
        qualification: Qualification filter (e.g., AS-Level, A2-Level)
        unit: Unit number filter
        processed: If True, only return exams that have been processed;
                 if False, only return exams that have not been processed
    
    Returns:
        List[Tuple[str, Dict[str, Any]]]: Filtered list of (exam path, exam data) pairs
    """
    filteredExams = []
    
    for examPath, exam in allExams:
        # Apply filters
        pathComponents = examPath.split(' / ')
        examSubject = pathComponents[0] if len(pathComponents) > 0 else ""
        examYear = pathComponents[1] if len(pathComponents) > 1 else ""
        examQualification = pathComponents[2] if len(pathComponents) > 2 else ""
        
        # Check each filter condition
        if subject and subject.lower() != examSubject.lower():
            continue
            
        if year and str(year) != examYear:
            continue
            
        if qualification and qualification.lower() not in examQualification.lower():
            continue
            
        if unit is not None:
            # Check if any document has the specified unit number
            unitMatch = False
            for docType, docs in exam.get('documents', {}).items():
                for doc in docs:
                    if doc.get('unit_number') == unit:
                        unitMatch = True
                        break
                if unitMatch:
                    break
            if not unitMatch:
                continue
        
        if processed is not None:
            # Check if any document has been processed
            hasProcessed = False
            for docType, docs in exam.get('documents', {}).items():
                for doc in docs:
                    if 'processed_at' in doc:
                        hasProcessed = True
                        break
                if hasProcessed:
                    break
            
            if processed != hasProcessed:
                continue
        
        filteredExams.append((examPath, exam))
    
    return filteredExams


def processOneExam(
    examParser: ExamContentParser,
    examPath: str,
    examData: Dict[str, Any],
    logger: logging.Logger
) -> bool:
    """
    Process a single exam.
    
    Args:
        examParser (ExamContentParser): Exam content parser instance
        examPath (str): Path to the exam in the index
        examData (Dict[str, Any]): Exam data from the index
        logger (logging.Logger): Logger instance
        
    Returns:
        bool: True if processing was successful, False otherwise
    """
    logger.info(f"Processing exam: {examPath}")
    startTime = time.time()
    
    try:
        success = examParser.process_exam_from_index(examData)
        elapsedTime = time.time() - startTime
        
        if success:
            logger.info(f"Successfully processed exam {examPath} in {elapsedTime:.2f} seconds")
        else:
            logger.error(f"Failed to process exam {examPath}")
        
        return success
    except Exception as e:
        logger.exception(f"Error processing exam {examPath}: {str(e)}")
        return False


def processMultipleExams(
    examParser: ExamContentParser,
    exams: List[Tuple[str, Dict[str, Any]]],
    logger: logging.Logger,
    limit: Optional[int] = None,
    continueOnError: bool = False
) -> Tuple[int, int]:
    """
    Process multiple exams.
    
    Args:
        examParser (ExamContentParser): Exam content parser instance
        exams (List[Tuple[str, Dict[str, Any]]]): List of (exam path, exam data) pairs
        logger (logging.Logger): Logger instance
        limit (Optional[int]): Maximum number of exams to process
        continueOnError (bool): Whether to continue processing after an error
        
    Returns:
        Tuple[int, int]: (number of successful exams, total exams processed)
    """
    successCount = 0
    totalCount = 0
    
    # Apply limit if specified
    if limit is not None and limit > 0:
        exams = exams[:limit]
    
    logger.info(f"Processing {len(exams)} exams")
    
    # Create progress bar
    for examPath, examData in tqdm(exams, desc="Processing exams", unit="exam"):
        try:
            success = processOneExam(examParser, examPath, examData, logger)
            if success:
                successCount += 1
            totalCount += 1
            
        except Exception as e:
            logger.exception(f"Error processing exam {examPath}: {str(e)}")
            if not continueOnError:
                logger.error("Stopping due to error")
                break
    
    logger.info(f"Processing complete. {successCount}/{totalCount} exams processed successfully.")
    return successCount, totalCount


def testExamParser(args: argparse.Namespace, logger: logging.Logger) -> int:
    """
    Test the ExamContentParser on a single valid exam.
    
    Args:
        args (argparse.Namespace): Command-line arguments
        logger (logging.Logger): Logger instance
        
    Returns:
        int: Exit code (0 for success, non-zero for errors)
    """
    logger.info("Starting exam parser test")
    
    # Load the hierarchical index
    try:
        indexData = loadHierarchicalIndex(args.index)
        logger.info(f"Successfully loaded index from {args.index}")
    except Exception as e:
        logger.error(f"Failed to load index: {str(e)}")
        return 1
    
    # Find valid exams
    allExams = findAllExams(indexData)
    if not allExams:
        logger.error("No valid exams found with both question paper and mark scheme")
        return 1
    
    # If exam ID provided, find that specific exam
    testExam = None
    if args.exam_id:
        for examPath, exam in allExams:
            # Check if any document in the exam matches the specified ID
            for docType, docs in exam.get('documents', {}).items():
                for doc in docs:
                    if doc.get('id') == args.exam_id:
                        testExam = (examPath, exam)
                        break
                if testExam:
                    break
            if testExam:
                break
        
        if not testExam:
            logger.error(f"No exam found with ID {args.exam_id}")
            return 1
    else:
        # Use the first valid exam
        testExam = allExams[0]
    
    examPath, exam = testExam
    logger.info(f"Using exam for testing: {examPath}")
    
    # Initialize the LLM client
    try:
        llmClient = MistralLLMClient(
            api_key=os.environ.get('MISTRAL_API_KEY', args.api_key),
            model=args.model
        )
        logger.info(f"Initialized LLM client with model: {args.model}")
    except Exception as e:
        logger.error(f"Failed to initialize LLM client: {str(e)}")
        return 1
    
    # Initialize the ExamContentParser
    try:
        examParser = ExamContentParser(
            llm_client=llmClient,
            index_path=args.index,
            ocr_results_path=args.ocr_results,
            log_level=logging.getLevelName(args.log_level.upper())
        )
        logger.info("Initialized ExamContentParser")
    except Exception as e:
        logger.error(f"Failed to initialize ExamContentParser: {str(e)}")
        return 1
    
    # Process the exam
    return 0 if processOneExam(examParser, examPath, exam, logger) else 1


def processCommand(args: argparse.Namespace, logger: logging.Logger) -> int:
    """
    Process exams based on command-line arguments.
    
    Args:
        args (argparse.Namespace): Command-line arguments
        logger (logging.Logger): Logger instance
        
    Returns:
        int: Exit code (0 for success, non-zero for errors)
    """
    logger.info(f"Processing exams with parameters: {args}")
    
    # Load the hierarchical index
    try:
        indexData = loadHierarchicalIndex(args.index)
        logger.info(f"Successfully loaded index from {args.index}")
    except Exception as e:
        logger.error(f"Failed to load index: {str(e)}")
        return 1
    
    # Find all valid exams
    allExams = findAllExams(indexData)
    logger.info(f"Found {len(allExams)} valid exams with both question paper and mark scheme")
    
    # Filter exams based on criteria
    filteredExams = filterExamsByCriteria(
        allExams,
        subject=args.subject,
        year=args.year,
        qualification=args.qualification,
        unit=args.unit,
        processed=False if args.skip_processed else None
    )
    
    logger.info(f"After filtering, {len(filteredExams)} exams will be processed")
    
    if not filteredExams:
        logger.warning("No exams match the specified criteria")
        return 0
    
    # Initialize the LLM client
    try:
        llmClient = MistralLLMClient(
            api_key=os.environ.get('MISTRAL_API_KEY', args.api_key),
            model=args.model
        )
        logger.info(f"Initialized LLM client with model: {args.model}")
    except Exception as e:
        logger.error(f"Failed to initialize LLM client: {str(e)}")
        return 1
    
    # Initialize the ExamContentParser
    try:
        examParser = ExamContentParser(
            llm_client=llmClient,
            index_path=args.index,
            ocr_results_path=args.ocr_results,
            log_level=logging.getLevelName(args.log_level.upper())
        )
        logger.info("Initialized ExamContentParser")
    except Exception as e:
        logger.error(f"Failed to initialize ExamContentParser: {str(e)}")
        return 1
    
    # Process exams
    successCount, totalCount = processMultipleExams(
        examParser=examParser,
        exams=filteredExams,
        logger=logger,
        limit=args.limit,
        continueOnError=args.continue_on_error
    )
    
    # Return success code only if all exams were processed successfully
    return 0 if successCount == totalCount else 1


def processSingleExam(args: argparse.Namespace, logger: logging.Logger) -> int:
    """
    Process a single exam specified by ID.
    
    Args:
        args (argparse.Namespace): Command-line arguments
        logger (logging.Logger): Logger instance
        
    Returns:
        int: Exit code (0 for success, non-zero for errors)
    """
    if not args.exam_id:
        logger.error("No exam ID provided")
        return 1
    
    logger.info(f"Processing single exam with ID: {args.exam_id}")
    
    # Load the hierarchical index
    try:
        indexData = loadHierarchicalIndex(args.index)
        logger.info(f"Successfully loaded index from {args.index}")
    except Exception as e:
        logger.error(f"Failed to load index: {str(e)}")
        return 1
    
    # Find the exam by ID
    targetExam = None
    
    for subjectName, subject in indexData.get('subjects', {}).items():
        for year, yearData in subject.get('years', {}).items():
            for qualName, qualification in yearData.get('qualifications', {}).items():
                for examName, exam in qualification.get('exams', {}).items():
                    examPath = f"{subjectName} / {year} / {qualName} / {examName}"
                    # Check document IDs
                    for docType, docs in exam.get('documents', {}).items():
                        for doc in docs:
                            if doc.get('id') == args.exam_id:
                                logger.info(f"Found exam for ID {args.exam_id}: {examPath}")
                                targetExam = (examPath, exam)
                                break
                        if targetExam:
                            break
                    if targetExam:
                        break
                if targetExam:
                    break
            if targetExam:
                break
        if targetExam:
            break
    
    if not targetExam:
        logger.error(f"No exam found with ID {args.exam_id}")
        return 1
    
    # Initialize the LLM client
    try:
        llmClient = MistralLLMClient(
            api_key=os.environ.get('MISTRAL_API_KEY', args.api_key),
            model=args.model
        )
        logger.info(f"Initialized LLM client with model: {args.model}")
    except Exception as e:
        logger.error(f"Failed to initialize LLM client: {str(e)}")
        return 1
    
    # Initialize the ExamContentParser
    try:
        examParser = ExamContentParser(
            llm_client=llmClient,
            index_path=args.index,
            ocr_results_path=args.ocr_results,
            log_level=logging.getLevelName(args.log_level.upper())
        )
        logger.info("Initialized ExamContentParser")
    except Exception as e:
        logger.error(f"Failed to initialize ExamContentParser: {str(e)}")
        return 1
    
    # Process the exam
    examPath, exam = targetExam
    return 0 if processOneExam(examParser, examPath, exam, logger) else 1


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
    parser.add_argument(
        '--api-key',
        help='Mistral API key (if not set via MISTRAL_API_KEY environment variable)'
    )
    parser.add_argument(
        '--logs-dir',
        help='Directory where log files should be saved (optional)'
    )
    
    # Add subparsers for different commands
    subparsers = parser.add_subparsers(
        title='commands',
        dest='command',
        help='Command to execute',
        required=False  # Changed from True to False to allow default command
    )
    
    # Test command
    testParser = subparsers.add_parser(
        'test',
        help='Test exam content parsing on a specific exam or the first valid exam'
    )
    testParser.add_argument(
        '--exam-id',
        help='ID of a specific exam to test'
    )
    
    # Process command for batch processing
    processParser = subparsers.add_parser(
        'process',
        help='Process multiple exams based on criteria'
    )
    processParser.add_argument(
        '--subject',
        help='Process exams for a specific subject'
    )
    processParser.add_argument(
        '--year',
        type=int,
        help='Process exams from a specific year'
    )
    processParser.add_argument(
        '--qualification',
        help='Process exams for a specific qualification (AS-Level, A2-Level, etc.)'
    )
    processParser.add_argument(
        '--unit',
        type=int,
        help='Process exams for a specific unit number'
    )
    processParser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of exams to process'
    )
    processParser.add_argument(
        '--skip-processed',
        action='store_true',
        help='Skip exams that have already been processed'
    )
    processParser.add_argument(
        '--continue-on-error',
        action='store_true',
        help='Continue processing exams even if one fails'
    )
    
    # Single exam command
    singleParser = subparsers.add_parser(
        'process-single',
        help='Process a single exam by its ID'
    )
    singleParser.add_argument(
        'exam_id',
        help='ID of the exam to process'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Set up logging
    logger = setupLogging(args.log_level, args.logs_dir)
    
    # Default to test command if no command is specified
    if not args.command:
        logger.info("No command specified, defaulting to 'test'")
        args.command = 'test'
        
    try:
        # Execute the appropriate function for the specified command
        if args.command == 'test':
            return testExamParser(args, logger)
        elif args.command == 'process':
            return processCommand(args, logger)
        elif args.command == 'process-single':
            return processSingleExam(args, logger)
        else:
            logger.error(f"Unknown command: {args.command}")
            return 1
    except Exception as e:
        logger.exception(f"Command execution failed: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
