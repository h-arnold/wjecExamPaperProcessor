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