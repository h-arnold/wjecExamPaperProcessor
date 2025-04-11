#!/usr/bin/env python3
"""
Script to transform the flat document index into a hierarchical structure.
"""

import sys
import json
import argparse

# Try relative import first (when used as a package), fall back to direct import (when run as script)
try:
    from .index_manager import IndexManager
    from .index_transformer import IndexStructureTransformer
except ImportError:
    # When run directly as a script
    from index_manager import IndexManager
    from index_transformer import IndexStructureTransformer

def main():
    """
    Main function to transform the index structure.
    """
    parser = argparse.ArgumentParser(
        description='Transform flat document index into a hierarchical structure'
    )
    parser.add_argument(
        '--input',
        default='Index/index.json',
        help='Path to input flat index file (default: Index/index.json)'
    )
    parser.add_argument(
        '--output',
        default='Index/hierarchical_index.json',
        help='Path for output hierarchical index file (default: Index/hierarchical_index.json)'
    )
    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='Run in non-interactive mode (automatically select first option for conflicts)'
    )
    parser.add_argument(
        '--skip-metadata',
        action='store_true',
        help='Skip enhancing the structure with document metadata'
    )
    parser.add_argument(
        '--transform-only',
        action='store_true',
        help='Only transform the structure without enhancing with metadata'
    )
    parser.add_argument(
        '--enhance-only',
        action='store_true',
        help='Only enhance existing hierarchical structure with metadata (skip transformation)'
    )
    
    args = parser.parse_args()
    
    try:
        if args.enhance_only and args.transform_only:
            print("Error: Cannot specify both --transform-only and --enhance-only")
            return 1
            
        # Initialize index manager with existing index
        index_manager = IndexManager(args.input)
        
        # Check if we have documents to transform
        if not index_manager.index["documents"] and not args.enhance_only:
            print(f"No documents found in the index at {args.input}")
            return 1
        
        # Create transformer
        transformer = IndexStructureTransformer(
            index_manager=index_manager,
            output_path=args.output,
            interactive=not args.non_interactive
        )
        
        # Transform the structure if not enhance-only
        if not args.enhance_only:
            print(f"Transforming index with {len(index_manager.index['documents'])} documents...")
            new_structure = transformer.transform()
            
            # Print summary of transformation
            subject_count = len(new_structure["subjects"])
            exam_count = 0
            for subject in new_structure["subjects"].values():
                for year in subject["years"].values():
                    for qualification in year["qualifications"].values():
                        exam_count += len(qualification["exams"])
            
            print(f"\nTransformation complete:")
            print(f"- Original document count: {len(index_manager.index['documents'])}")
            print(f"- Subjects: {subject_count}")
            print(f"- Exam units: {exam_count}")
            print(f"- Structure saved to: {args.output}")
        
        # Enhance with metadata if not transform-only and not skip-metadata
        if not args.transform_only and not args.skip_metadata:
            # If we're only enhancing, load the existing structure
            if args.enhance_only:
                try:
                    with open(args.output, 'r', encoding='utf-8') as f:
                        transformer.new_structure = json.load(f)
                    print(f"Loaded existing hierarchical structure from {args.output}")
                except (json.JSONDecodeError, FileNotFoundError) as e:
                    print(f"Error: Could not load existing structure from {args.output}: {str(e)}")
                    return 1
            
            # Enhance the structure with metadata from document files
            enhanced_structure = transformer.enhance_with_document_metadata()
            print(f"Enhanced structure saved to: {args.output}")
            
    except Exception as e:
        print(f"Error during processing: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())