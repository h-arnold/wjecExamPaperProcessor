#!/usr/bin/env python3
"""
Unified command line interface for the WJEC Question Tagger.
This script provides a convenient interface for tagging exam questions with specification areas.
"""

import argparse
import logging
import os
from dotenv import load_dotenv
import sys
from pathlib import Path

from dotenv import load_dotenv

# Set up workspace root path
WORKSPACE_ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
os.chdir(WORKSPACE_ROOT)
load_dotenv()

try:
    from .question_tagger import QuestionTagger
except ImportError:
    # When run directly as script
    from question_tagger import QuestionTagger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """
    Main function for the unified question tagging workflow.
    
    This function parses command-line arguments and runs the QuestionTagger
    with the specified options.
    """
    parser = argparse.ArgumentParser(
        description='Tag WJEC exam questions with specification areas'
    )
    parser.add_argument(
        '--input',
        default='Index/final_index.json',
        help='Path to input index file (default: Index/final_index.json)'
    )
    parser.add_argument(
        '--output',
        help='Path for output tagged index file (default: input_filename_tagged.json)'
    )
    parser.add_argument(
        '--llm-provider',
        default='openai',
        choices=['openai', 'mistral'],
        help='LLM provider to use (default: openai)'
    )
    parser.add_argument(
        '--llm-model',
        default='gpt-4.1-mini',
        help='LLM model to use (default: gpt-4.1-mini)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry-run mode (does not make actual API calls)'
    )
    parser.add_argument(
        '--no-validate',
        action='store_true',
        help='Disable validation of specification tags'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set verbose logging if requested
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
   
    try:
        # Initialize the question tagger
        logger.info(f"Initializing QuestionTagger with {args.llm_provider}/{args.llm_model}")
        
        tagger = QuestionTagger(
            indexPath=args.input,
            llmProvider=args.llm_provider,
            llmModel=args.llm_model,
            dryRun=args.dry_run,
            outputPath=args.output,
            validateTags=not args.no_validate
        )
        

        logger.info("Processing all questions in the index")
        tagger.processIndex()
        logger.info("Processing completed successfully")
        return 0
            
    except Exception as e:
        logger.error(f"Error during processing: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())