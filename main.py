#!/usr/bin/env python3
"""
WJEC Exam Paper Processor - Main Entry Point

This script serves as the unified entry point for all functionality in the WJEC Exam Paper Processor.
It can:
1. Run the OCR processing pipeline (src/main.py)
2. Extract metadata from OCR results (src/MetadataExtraction/main.py)
3. Manage, transform, and enhance the index (src/IndexManager/main.py)
4. Process exam content to extract structured questions (src/ExamContentParser/main.py)
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Ensure the src directory is in the path
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

def main():
    """
    Main entry point for the WJEC Exam Paper Processor.
    Parses command-line arguments and dispatches to the appropriate functionality.
    """
    parser = argparse.ArgumentParser(
        description='WJEC Exam Paper Processor - Process exam PDFs, extract metadata, and manage the index'
    )
    
    # Create subparsers for different functionality
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # OCR processing subcommand
    ocr_parser = subparsers.add_parser('ocr', help='Run the OCR processing pipeline')
    ocr_parser.add_argument(
        '--source',
        help='Source directory containing PDF files'
    )
    ocr_parser.add_argument(
        '--dest',
        help='Destination directory for OCR results'
    )
    ocr_parser.add_argument(
        '--api-key', '-k',
        help='Mistral API key (can also be set via MISTRAL_API_KEY environment variable)'
    )
    
    # Metadata extraction subcommand
    metadata_parser = subparsers.add_parser('metadata', help='Extract metadata from OCR results')
    metadata_parser.add_argument(
        '--file', '-f',
        help='Path to a single OCR JSON file to process'
    )
    metadata_parser.add_argument(
        '--directory', '-d',
        default="ocr_results",
        help='Path to directory containing OCR JSON files'
    )
    metadata_parser.add_argument(
        '--pattern', '-p',
        default='*.json',
        help='Glob pattern for matching OCR files (default: *.json)'
    )
    metadata_parser.add_argument(
        '--metadata-dir',
        default='metadata',
        help='Base directory for metadata files (default: metadata)'
    )
    metadata_parser.add_argument(
        '--index',
        default='index.json',
        help='Path to the index file (default: index.json)'
    )
    metadata_parser.add_argument(
        '--provider',
        default='mistral',
        choices=['mistral'],
        help='LLM provider to use (default: mistral)'
    )
    metadata_parser.add_argument(
        '--api-key', '-k',
        help='LLM API key (can also be set via environment variable)'
    )
    
    # Index management subcommand
    index_parser = subparsers.add_parser('index', help='Manage, transform, and enhance the index')
    index_parser.add_argument(
        '--input',
        default='Index/index.json',
        help='Path to input flat index file (default: Index/index.json)'
    )
    index_parser.add_argument(
        '--output',
        default='Index/hierarchical_index.json',
        help='Path for output hierarchical index file (default: Index/hierarchical_index.json)'
    )
    index_parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='Run in non-interactive mode (automatically select first option for conflicts)'
    )
    index_parser.add_argument(
        '--update-only',
        action='store_true',
        help='Only update unit numbers and relationships (skip transformation and enhancement)'
    )
    index_parser.add_argument(
        '--transform-only',
        action='store_true',
        help='Only transform the structure (skip enhancement)'
    )
    index_parser.add_argument(
        '--enhance-only',
        action='store_true',
        help='Only enhance existing hierarchical structure (skip updating and transformation)'
    )
    index_parser.add_argument(
        '--skip-metadata',
        action='store_true',
        help='Skip enhancing the structure with document metadata'
    )
    
    # Exam content parser subcommand
    exam_content_parser = subparsers.add_parser('exam-content', help='Process exam content to extract questions and mark schemes')
    exam_content_parser.add_argument(
        '--index',
        default='Index/hierarchical_index.json',
        help='Path to hierarchical index file (default: Index/hierarchical_index.json)'
    )
    exam_content_parser.add_argument(
        '--ocr-results',
        default='ocr_results',
        help='Path to OCR results directory (default: ocr_results)'
    )
    exam_content_parser.add_argument(
        '--output',
        default='Index/questions_index.json',
        help='Path for output questions index file (default: Index/questions_index.json)'
    )
    exam_content_parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Set the logging level (default: INFO)'
    )
    exam_content_parser.add_argument(
        '--model',
        default='mistral-medium',
        help='Mistral model to use for content parsing (default: mistral-medium)'
    )
    exam_content_parser.add_argument(
        '--api-key',
        help='Mistral API key (if not set via MISTRAL_API_KEY environment variable)'
    )
    exam_content_parser.add_argument(
        '--logs-dir',
        help='Directory where log files should be saved (optional)'
    )
    
    # Add exam-content subcommands
    exam_content_subparsers = exam_content_parser.add_subparsers(
        title='exam-content-commands',
        dest='exam_content_command',
        help='Exam content command to execute'
    )
    
    # Test command for exam content
    exam_test_parser = exam_content_subparsers.add_parser(
        'test',
        help='Test exam content parsing on a specific exam or the first valid exam'
    )
    exam_test_parser.add_argument(
        '--exam-id',
        help='ID of a specific exam to test'
    )
    
    # Process command for batch processing
    exam_process_parser = exam_content_subparsers.add_parser(
        'process',
        help='Process multiple exams based on criteria'
    )
    exam_process_parser.add_argument(
        '--subject',
        help='Process exams for a specific subject'
    )
    exam_process_parser.add_argument(
        '--year',
        type=int,
        help='Process exams from a specific year'
    )
    exam_process_parser.add_argument(
        '--qualification',
        help='Process exams for a specific qualification (AS-Level, A2-Level, etc.)'
    )
    exam_process_parser.add_argument(
        '--unit',
        type=int,
        help='Process exams for a specific unit number'
    )
    exam_process_parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of exams to process'
    )
    exam_process_parser.add_argument(
        '--skip-processed',
        action='store_true',
        help='Skip exams that have already been processed'
    )
    exam_process_parser.add_argument(
        '--continue-on-error',
        action='store_true',
        help='Continue processing exams even if one fails'
    )
    
    # Single exam command
    exam_single_parser = exam_content_subparsers.add_parser(
        'process-single',
        help='Process a single exam by its ID'
    )
    exam_single_parser.add_argument(
        'exam_id',
        help='ID of the exam to process'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # If no command specified, show help and exit
    if not args.command:
        parser.print_help()
        return 1
    
    # Dispatch to the appropriate functionality
    try:
        if args.command == 'ocr':
            # Run the OCR processing pipeline
            from src.main import main as ocr_main
            
            # Set environment variables for OCR processing
            if args.source:
                os.environ["SOURCE_FOLDER"] = args.source
            if args.dest:
                os.environ["DESTINATION_FOLDER"] = args.dest
            if args.api_key:
                os.environ["MISTRAL_API_KEY"] = args.api_key
                
            return ocr_main()
            
        elif args.command == 'metadata':
            # Run the metadata extraction pipeline
            from src.MetadataExtraction.main import main as metadata_main
            
            # Replace sys.argv with the arguments for the metadata extraction script
            sys.argv = [sys.argv[0]]
            if args.file:
                sys.argv.extend(['--file', args.file])
            if args.directory:
                sys.argv.extend(['--directory', args.directory])
            if args.pattern:
                sys.argv.extend(['--pattern', args.pattern])
            if args.metadata_dir:
                sys.argv.extend(['--metadata-dir', args.metadata_dir])
            if args.index:
                sys.argv.extend(['--index', args.index])
            if args.provider:
                sys.argv.extend(['--provider', args.provider])
            if args.api_key:
                sys.argv.extend(['--api-key', args.api_key])
                
            return metadata_main()
            
        elif args.command == 'index':
            # Run the index management pipeline
            from src.IndexManager.main import main as index_main
            
            # Replace sys.argv with the arguments for the index management script
            sys.argv = [sys.argv[0]]
            if args.input:
                sys.argv.extend(['--input', args.input])
            if args.output:
                sys.argv.extend(['--output', args.output])
            if args.non_interactive:
                sys.argv.append('--non-interactive')
            if args.update_only:
                sys.argv.append('--update-only')
            if args.transform_only:
                sys.argv.append('--transform-only')
            if args.enhance_only:
                sys.argv.append('--enhance-only')
            if args.skip_metadata:
                sys.argv.append('--skip-metadata')
                
            return index_main()
            
        elif args.command == 'exam-content':
            # Run the exam content parser
            from src.ExamContentParser.main import main as exam_content_main
            
            # Build command line arguments for the exam content parser
            sys.argv = [sys.argv[0]]
            
            # Add common arguments
            if args.index:
                sys.argv.extend(['--index', args.index])
            if args.ocr_results:
                sys.argv.extend(['--ocr-results', args.ocr_results])
            if args.output:
                sys.argv.extend(['--output', args.output])
            if args.log_level:
                sys.argv.extend(['--log-level', args.log_level])
            if args.model:
                sys.argv.extend(['--model', args.model])
            if args.api_key:
                sys.argv.extend(['--api-key', args.api_key])
            if args.logs_dir:
                sys.argv.extend(['--logs-dir', args.logs_dir])
            
            # Add subcommand and its arguments
            if args.exam_content_command:
                sys.argv.append(args.exam_content_command)
                
                if args.exam_content_command == 'test' and args.exam_id:
                    sys.argv.extend(['--exam-id', args.exam_id])
                    
                elif args.exam_content_command == 'process':
                    if args.subject:
                        sys.argv.extend(['--subject', args.subject])
                    if args.year:
                        sys.argv.extend(['--year', str(args.year)])
                    if args.qualification:
                        sys.argv.extend(['--qualification', args.qualification])
                    if args.unit:
                        sys.argv.extend(['--unit', str(args.unit)])
                    if args.limit:
                        sys.argv.extend(['--limit', str(args.limit)])
                    if args.skip_processed:
                        sys.argv.append('--skip-processed')
                    if args.continue_on_error:
                        sys.argv.append('--continue-on-error')
                        
                elif args.exam_content_command == 'process-single' and args.exam_id:
                    sys.argv.append(args.exam_id)
            
            return exam_content_main()
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
