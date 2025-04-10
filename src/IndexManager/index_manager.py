"""
Index manager for maintaining the master index of exam documents.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional


class IndexManager:
    """
    Manages the master index of exam documents.
    
    The index maintains metadata about all processed documents and their relationships,
    serving as a central registry for document lookup and search operations.
    """
    
    def __init__(self, index_path: str = "index.json"):
        """
        Initialize the index manager.
        
        Args:
            index_path (str): Path to the index file
        """
        self.index_path = Path(index_path)
        self.index = self._initialize_index()
        
    def _initialize_index(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load index from disk or create new if it doesn't exist.
        
        Returns:
            Dict: The loaded or newly created index
        """
        if self.index_path.exists():
            try:
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                # If index file is corrupted, create new
                return {"documents": []}
        else:
            return {"documents": []}
    
    def save_index(self):
        """
        Save the index to disk.
        
        Raises:
            IOError: If there is an error writing to the index file
        """
        try:
            with open(self.index_path, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise IOError(f"Failed to save index to {self.index_path}: {str(e)}")
    
    def find_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a document in the index by its ID.
        
        Args:
            document_id (str): The ID of the document to find
            
        Returns:
            Dict or None: The document entry or None if not found
        """
        for doc in self.index["documents"]:
            if doc.get("id") == document_id:
                return doc
        return None
    
    def _extract_unit_number(self, exam_paper: str) -> Optional[int]:
        """
        Extract unit number from exam paper title.
        
        Args:
            exam_paper (str): The exam paper title
            
        Returns:
            int or None: The unit number if found, otherwise None
        """
        if not exam_paper:
            return None
            
        # Look for patterns like "Unit 3" or "unit 3" or "Unit3"
        unit_patterns = [
            r'unit\s*(\d)',  # matches "Unit 3" or "unit3"
            r'Unit\s*(\d)',  # matches "Unit 3" or "Unit3"
            r'UNIT\s*(\d)',  # matches "UNIT 3" or "UNIT3"
            r'u(\d+)-',      # matches "u30-" in exam codes like "1500u30-1"
            r'U(\d+)-',      # matches "U30-" in exam codes like "1500U30-1"
            r'u(\d+)\w',     # matches "u30" in exam codes
            r'U(\d+)\w'      # matches "U30" in exam codes
        ]
        
        for pattern in unit_patterns:
            match = re.search(pattern, exam_paper, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue
                    
        return None
        
    def update_index(self, metadata: Dict[str, Any], content_path: str, 
                     metadata_path: str) -> Dict[str, Any]:
        """
        Add or update document in the index.
        
        Args:
            metadata (Dict[str, Any]): Document metadata
            content_path (str): Path to the OCR content file
            metadata_path (str): Path to the metadata file
            
        Returns:
            Dict[str, Any]: The added or updated index entry
        """
        # Extract ID from content path
        document_id = Path(content_path).stem
        
        # Extract unit number from exam paper title
        unit_number = self._extract_unit_number(metadata.get("Exam Paper", ""))
        if unit_number is None and document_id:
            # Try to extract from document ID if not found in exam paper
            unit_number = self._extract_unit_number(document_id)
        
        # Create index entry
        index_entry = {
            "id": document_id,
            "type": metadata.get("Type"),
            "year": metadata.get("Year"),
            "qualification": metadata.get("Qualification"),
            "subject": metadata.get("Subject"),
            "exam_paper": metadata.get("Exam Paper"),
            "exam_season": metadata.get("Exam Season"),
            "content_path": str(content_path),
            "metadata_path": str(metadata_path),
            "unit_number": unit_number,
            "related_documents": []
        }
        
        # Check if document already exists in index
        existing_doc = self.find_document_by_id(document_id)
        if existing_doc:
            # Update existing entry
            existing_doc.update(index_entry)
            # Preserve related documents
            if "related_documents" in existing_doc and existing_doc["related_documents"]:
                index_entry["related_documents"] = existing_doc["related_documents"]
            
            # Find document index and update it
            for i, doc in enumerate(self.index["documents"]):
                if doc.get("id") == document_id:
                    self.index["documents"][i] = index_entry
                    break
        else:
            # Add new entry
            self.index["documents"].append(index_entry)
        
        # Try to find related documents
        self._update_related_documents(document_id)
        
        # Save index
        self.save_index()
        
        return index_entry
    
    def find_related_documents(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Find related documents based on ID patterns and metadata.
        
        For example, find mark scheme for a question paper or vice versa.
        
        Args:
            document_id (str): The document ID to find relations for
            
        Returns:
            List[Dict[str, Any]]: List of related documents
        """
        related_docs = []
        doc = self.find_document_by_id(document_id)
        
        if not doc:
            return []
            
        for related_id in doc.get("related_documents", []):
            related = self.find_document_by_id(related_id)
            if related:
                related_docs.append(related)
                
        return related_docs
    
    def _update_related_documents(self, document_id: str):
        """
        Update related documents for the given document ID.
        
        This method uses filename patterns to detect relationships
        (e.g., s23-2500u20-1a.json and s23-2500u20-1-ms.json).
        
        Args:
            document_id (str): The document ID to update relations for
        """
        doc = self.find_document_by_id(document_id)
        if not doc:
            return
            
        # For question papers, look for mark schemes
        if doc.get("type") == "Question Paper":
            # Try different patterns based on common WJEC naming conventions
            patterns = [
                # s23-2500u20-1a -> s23-2500u20-1-ms
                lambda id: re.sub(r'(\w+)-(\d+[a-z]*\d*)-(\d+)([a-z])', r'\1-\2-\3-ms', id),
                # 2500U20-1 -> 2500U20-1-ms
                lambda id: f"{id}-ms"
            ]
            
            for pattern_func in patterns:
                possible_ms_id = pattern_func(document_id)
                ms_doc = self.find_document_by_id(possible_ms_id)
                if ms_doc and ms_doc.get("type") == "Mark Scheme":
                    if possible_ms_id not in doc["related_documents"]:
                        doc["related_documents"].append(possible_ms_id)
                    
                    # Also update the mark scheme to reference back
                    if document_id not in ms_doc.get("related_documents", []):
                        if "related_documents" not in ms_doc:
                            ms_doc["related_documents"] = []
                        ms_doc["related_documents"].append(document_id)
                    break
                    
        # For mark schemes, look for question papers
        elif doc.get("type") == "Mark Scheme":
            # Strip the -ms suffix to find the question paper
            if "-ms" in document_id.lower():
                possible_qp_id = document_id.lower().replace("-ms", "")
                qp_doc = self.find_document_by_id(possible_qp_id)
                if qp_doc and qp_doc.get("type") == "Question Paper":
                    if possible_qp_id not in doc["related_documents"]:
                        doc["related_documents"].append(possible_qp_id)
                        
                    # Also update the question paper to reference back
                    if document_id not in qp_doc.get("related_documents", []):
                        if "related_documents" not in qp_doc:
                            qp_doc["related_documents"] = []
                        qp_doc["related_documents"].append(document_id)
    
    def search_documents(self, 
                        criteria: Dict[str, Any] = None, 
                        query: str = None) -> List[Dict[str, Any]]:
        """
        Search documents based on metadata criteria.
        
        Args:
            criteria (Dict[str, Any], optional): Search criteria as field-value pairs
            query (str, optional): Text query to search in document titles
            
        Returns:
            List[Dict[str, Any]]: List of matching documents
        """
        results = []
        
        # If no criteria and no query, return all documents
        if not criteria and not query:
            return self.index["documents"]
            
        for doc in self.index["documents"]:
            # Check criteria match
            criteria_match = True
            if criteria:
                for key, value in criteria.items():
                    if key not in doc or doc[key] != value:
                        criteria_match = False
                        break
                        
            # Check text query match
            query_match = True
            if query and query.lower() not in str(doc).lower():
                query_match = False
                
            if criteria_match and query_match:
                results.append(doc)
                
        return results

    def sort_index(self):
        """
        Sort the index by subject, year, qualification, and unit_number.
        
        This helps organize the index to group related documents together.
        
        Returns:
            List[Dict[str, Any]]: The sorted list of documents
        """
        # First, ensure all documents have unit_number
        for doc in self.index["documents"]:
            if "unit_number" not in doc or doc["unit_number"] is None:
                # Try to extract from exam_paper field
                if "exam_paper" in doc and doc["exam_paper"]:
                    doc["unit_number"] = self._extract_unit_number(doc["exam_paper"])
                # Try to extract from id field
                if ("unit_number" not in doc or doc["unit_number"] is None) and "id" in doc:
                    doc["unit_number"] = self._extract_unit_number(doc["id"])
        
        # Sort the documents
        sorted_docs = sorted(
            self.index["documents"], 
            key=lambda x: (
                x.get("subject", ""), 
                x.get("year", 0), 
                x.get("qualification", ""), 
                x.get("unit_number", 0) if x.get("unit_number") is not None else 999
            )
        )
        
        # Update the index
        self.index["documents"] = sorted_docs
        self.save_index()
        
        return sorted_docs
        
    def find_related_by_unit(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Find related documents based on unit number, year, and qualification.
        
        This helps identify question papers and mark schemes that belong together
        even if they don't follow the standard naming pattern.
        
        Args:
            document_id (str): The document ID to find relations for
            
        Returns:
            List[Dict[str, Any]]: List of related documents
        """
        doc = self.find_document_by_id(document_id)
        if not doc:
            return []
            
        related = []
        
        # Only proceed if we have a unit number
        if "unit_number" not in doc or doc["unit_number"] is None:
            return []
            
        # Determine the document type we're looking for
        target_type = "Mark Scheme" if doc["type"] == "Question Paper" else "Question Paper"
        
        for other_doc in self.index["documents"]:
            # Skip self or documents that don't match our target type
            if other_doc["id"] == doc["id"] or other_doc["type"] != target_type:
                continue
                
            # Check for matching unit, year, subject, and qualification
            if (other_doc.get("unit_number") == doc["unit_number"] and
                other_doc.get("year") == doc.get("year") and
                other_doc.get("subject") == doc.get("subject") and
                other_doc.get("qualification") == doc.get("qualification")):
                related.append(other_doc)
                
                # Also update the relation in both documents
                if other_doc["id"] not in doc.get("related_documents", []):
                    if "related_documents" not in doc:
                        doc["related_documents"] = []
                    doc["related_documents"].append(other_doc["id"])
                    
                if doc["id"] not in other_doc.get("related_documents", []):
                    if "related_documents" not in other_doc:
                        other_doc["related_documents"] = []
                    other_doc["related_documents"].append(doc["id"])
        
        # Save the index with the new relationships
        self.save_index()
        return related
        
    def update_all_document_relations(self):
        """
        Update relationships for all documents in the index.
        
        This method processes all documents to find related question papers
        and mark schemes based on unit numbers and metadata.
        
        Returns:
            int: Number of relationships found and updated
        """
        relationship_count = 0
        
        # First ensure all documents have unit numbers
        for doc in self.index["documents"]:
            if "unit_number" not in doc or doc["unit_number"] is None:
                # Try to extract from exam_paper field
                if "exam_paper" in doc and doc["exam_paper"]:
                    doc["unit_number"] = self._extract_unit_number(doc["exam_paper"])
                # Try to extract from id field
                if ("unit_number" not in doc or doc["unit_number"] is None) and "id" in doc:
                    doc["unit_number"] = self._extract_unit_number(doc["id"])
        
        # Then find relationships
        for doc in self.index["documents"]:
            # Find related documents based on pattern matching
            self._update_related_documents(doc["id"])
            
            # Find related documents based on unit numbers
            related = self.find_related_by_unit(doc["id"])
            relationship_count += len(related)
        
        return relationship_count