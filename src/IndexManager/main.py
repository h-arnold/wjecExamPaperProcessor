#!/usr/bin/env python3
"""
Unified command line interface for index management, transformation, and enhancement.
This script combines the functionality of the previous scripts into a single interface.
"""

import argparse
import sys
from pathlib import Path

try:
    from .index_manager import IndexManager
except ImportError:
    # When run directly as script
    from index_manager import IndexManager

def main():
    """
    Main function for the unified index management workflow.
    """
    parser = argparse.ArgumentParser(
        description='Manage, transform, and enhance exam document index'
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
        '--update-only',
        action='store_true',
        help='Only update unit numbers and relationships (skip transformation and enhancement)'
    )
    parser.add_argument(
        '--transform-only',
        action='store_true',
        help='Only transform the structure (skip enhancement)'
    )
    parser.add_argument(
        '--enhance-only',
        action='store_true',
        help='Only enhance existing hierarchical structure (skip updating and transformation)'
    )
    parser.add_argument(
        '--skip-metadata',
        action='store_true',
        help='Skip enhancing the structure with document metadata'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize the index manager
        index_manager = IndexManager(args.input)
        
        # Check for contradictory flags
        if sum([args.update_only, args.transform_only, args.enhance_only]) > 1:
            print("Error: Cannot specify more than one of --update-only, --transform-only, and --enhance-only")
            return 1
            
        # Determine workflow based on flags
        if args.update_only:
            # Update unit numbers and relationships only
            print(f"Processing {len(index_manager.index['documents'])} documents...")
            
            updated_count = index_manager.update_unit_numbers()
            print(f"Added unit numbers to {updated_count} documents")
            
            index_manager.sort_index()
            print(f"Index sorted by subject, year, qualification, and unit number")
            
            relationship_count = index_manager.update_all_document_relations()
            print(f"Found {relationship_count} relationships between question papers and mark schemes")
            
            index_manager.save_index()
            print(f"Index successfully updated and saved to {index_manager.index_path}")
            
            # Display unit distribution
            unit_distribution = index_manager.get_unit_distribution()
            print("\nDistribution of documents by unit number:")
            for unit, count in sorted(unit_distribution.items()):
                print(f"Unit {unit}: {count} documents")
            
            # Display null units
            null_units = index_manager.get_documents_without_unit()
            if null_units:
                print(f"\nWarning: {len(null_units)} documents have no unit number:")
                for doc_id in null_units[:10]:  # Show only first 10
                    print(f"  - {doc_id}")
                if len(null_units) > 10:
                    print(f"  - ... and {len(null_units) - 10} more")
        elif args.enhance_only:
            # Enhance existing hierarchical structure only
            index_manager.enhance_hierarchical_structure(
                args.output, 
                interactive=not args.non_interactive
            )
        elif args.transform_only:
            # Transform only
            index_manager.transform_to_hierarchical(
                args.output, 
                interactive=not args.non_interactive
            )
        else:
            # Run full process
            if not args.skip_metadata:
                index_manager.run_full_process(
                    args.output, 
                    interactive=not args.non_interactive
                )
            else:
                # Update and transform, but skip enhancement
                print(f"Processing {len(index_manager.index['documents'])} documents...")
                
                updated_count = index_manager.update_unit_numbers()
                print(f"Added unit numbers to {updated_count} documents")
                
                index_manager.sort_index()
                print(f"Index sorted by subject, year, qualification, and unit number")
                
                relationship_count = index_manager.update_all_document_relations()
                print(f"Found {relationship_count} relationships between question papers and mark schemes")
                
                index_manager.save_index()
                print(f"Updated index saved to {index_manager.index_path}")
                
                index_manager.transform_to_hierarchical(
                    args.output, 
                    interactive=not args.non_interactive
                )
        
        print("\nProcessing completed successfully!")
        return 0
            
    except Exception as e:
        print(f"Error during processing: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())