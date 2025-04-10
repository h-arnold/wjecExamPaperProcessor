#!/usr/bin/env python3
"""
Main script for updating the index with unit numbers and establishing document relationships.
This uses the IndexManager class to organize documents by subject, year, qualification, and unit number.
"""

import sys
from typing import Dict, Any, List

# Try relative import first (when used as a package), fall back to direct import (when run as script)
try:
    from .index_manager import IndexManager
except ImportError:
    # When run directly as a script
    from index_manager import IndexManager

class IndexUpdater:
    """
    Class for updating the index with unit numbers and establishing document relationships.
    
    This class extends the functionality of IndexManager by providing methods
    to enhance the index with unit numbers and organize documents for better
    searchability and relationship mapping.
    """
    
    def __init__(self, index_path: str = "Index/index.json"):
        """
        Initialize the index updater.
        
        Args:
            index_path (str): Path to the index file
        """
        self.index_manager = IndexManager(index_path)
        
    def update_unit_numbers(self) -> int:
        """
        Update unit numbers for all documents in the index.
        
        Returns:
            int: Number of documents updated with unit numbers
        """
        documents_updated = 0
        
        for doc in self.index_manager.index['documents']:
            if 'unit_number' not in doc or doc['unit_number'] is None:
                # Use IndexManager's existing method to extract unit numbers
                unit_number = None
                if 'exam_paper' in doc and doc['exam_paper']:
                    unit_number = self.index_manager._extract_unit_number(doc['exam_paper'])
                
                if unit_number is None and 'id' in doc:
                    unit_number = self.index_manager._extract_unit_number(doc['id'])
                
                if unit_number is not None:
                    doc['unit_number'] = unit_number
                    documents_updated += 1
                else:
                    doc['unit_number'] = None
        
        return documents_updated
        
    def sort_index(self) -> List[Dict[str, Any]]:
        """
        Sort the index by subject, year, qualification, and unit_number.
        
        Returns:
            List[Dict[str, Any]]: The sorted list of documents
        """
        # Simply use the IndexManager's sort_index method which already handles
        # updating unit numbers internally
        return self.index_manager.sort_index()
        
    def update_relationships(self) -> int:
        """
        Update document relationships based on unit numbers and naming patterns.
        
        This delegates to the IndexManager's update_all_document_relations method.
        
        Returns:
            int: Number of relationships found
        """
        # Directly delegate to the IndexManager's method
        return self.index_manager.update_all_document_relations()
        
    def get_unit_distribution(self) -> Dict[int, int]:
        """
        Get distribution of documents by unit number.
        
        Returns:
            Dict[int, int]: Dictionary with unit numbers as keys and document counts as values
        """
        unit_counts = {}
        for doc in self.index_manager.index['documents']:
            if doc.get('unit_number') is not None:
                unit_number = doc['unit_number']
                unit_counts[unit_number] = unit_counts.get(unit_number, 0) + 1
        
        return unit_counts
        
    def get_documents_without_unit(self) -> List[str]:
        """
        Get list of documents without a unit number.
        
        Returns:
            List[str]: List of document IDs without a unit number
        """
        return [doc['id'] for doc in self.index_manager.index['documents'] 
                if doc.get('unit_number') is None]
    
    def save_index(self):
        """
        Save the updated index.
        """
        self.index_manager.save_index()
        
    def run_update_process(self) -> Dict[str, Any]:
        """
        Run the complete update process.
        
        Returns:
            Dict[str, Any]: Dictionary with update statistics
        """
        stats = {}
        
        # Update unit numbers
        docs_updated = self.update_unit_numbers()
        stats['documents_updated_with_unit'] = docs_updated
        
        # Sort index
        sorted_docs = self.sort_index()
        stats['documents_sorted'] = len(sorted_docs)
        
        # Update relationships
        relationships = self.update_relationships()
        stats['relationships_found'] = relationships
        
        # Get distribution and missing units
        stats['unit_distribution'] = self.get_unit_distribution()
        stats['documents_without_unit'] = self.get_documents_without_unit()
        
        # Save index
        self.save_index()
        stats['index_path'] = self.index_manager.index_path
        
        return stats


def main():
    """
    Main function to update the index with unit numbers and document relationships.
    """
    try:
        updater = IndexUpdater("Index/index.json")
        
        print(f"Processing {len(updater.index_manager.index['documents'])} documents...")
        
        # Run the update process
        stats = updater.run_update_process()
        
        # Output results
        print(f"Added unit numbers to {stats['documents_updated_with_unit']} documents")
        print(f"Index sorted by subject, year, qualification, and unit number")
        print(f"Found {stats['relationships_found']} relationships between question papers and mark schemes")
        print(f"Index successfully updated and saved to {stats['index_path']}")
        
        # Display unit distribution
        print("\nDistribution of documents by unit number:")
        for unit, count in sorted(stats['unit_distribution'].items()):
            print(f"Unit {unit}: {count} documents")
        
        # Display null units
        null_units = stats['documents_without_unit']
        if null_units:
            print(f"\nWarning: {len(null_units)} documents have no unit number:")
            for doc_id in null_units[:10]:  # Show only first 10
                print(f"  - {doc_id}")
            if len(null_units) > 10:
                print(f"  - ... and {len(null_units) - 10} more")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())