"""
Unified index manager for maintaining, transforming and enhancing the exam document index.

This module combines functionality from the previous IndexManager, IndexUpdater,
and IndexStructureTransformer classes into a single unified workflow.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict


class IndexManager:
    """
    Manages the master index of exam documents.
    
    The index maintains metadata about all processed documents and their relationships,
    supporting the entire workflow from index creation to hierarchical transformation.
    """
    
    def __init__(self, index_path: str = "index.json"):
        """
        Initialize the index manager.
        
        Args:
            index_path (str): Path to the index file
        """
        self.index_path = Path(index_path)
        self.index = self._initialize_index()
        # For hierarchical transformation
        self.hierarchical_structure = {"subjects": {}}
        self.document_mapping = {}
        
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
    
    def save_index(self, output_path: Optional[str] = None) -> bool:
        """
        Save the index to disk.
        
        Args:
            output_path: Optional alternate path to save the index to
            
        Returns:
            bool: True if save was successful
            
        Raises:
            IOError: If there is an error writing to the index file
        """
        save_path = Path(output_path) if output_path else self.index_path
        
        try:
            # Create parent directory if it doesn't exist
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            raise IOError(f"Failed to save index to {save_path}: {str(e)}")
    
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
    
    def _extract_unit_number(self, text: str) -> Optional[int]:
        """
        Extract unit number from exam paper title or document ID.
        
        Args:
            text (str): The text to extract unit number from
            
        Returns:
            int or None: The unit number if found, otherwise None
        """
        if not text:
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
            match = re.search(pattern, text, re.IGNORECASE)
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

    def sort_index(self) -> List[Dict[str, Any]]:
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

    def update_unit_numbers(self) -> int:
        """
        Update unit numbers for documents in the index based on exam paper field or ID.
        
        Returns:
            int: Number of documents updated with unit numbers
        """
        documents_updated = 0
        
        for doc in self.index["documents"]:
            if "unit_number" not in doc or doc["unit_number"] is None:
                # Try to extract from exam_paper field
                if "exam_paper" in doc and doc["exam_paper"]:
                    unit_number = self._extract_unit_number(doc["exam_paper"])
                    if unit_number is not None:
                        doc["unit_number"] = unit_number
                        documents_updated += 1
                        continue
                
                # Try to extract from id field
                if "id" in doc:
                    unit_number = self._extract_unit_number(doc["id"])
                    if unit_number is not None:
                        doc["unit_number"] = unit_number
                        documents_updated += 1
                    else:
                        doc["unit_number"] = None
        
        return documents_updated
        
    def update_all_document_relations(self) -> int:
        """
        Update relationships for all documents in the index.
        
        This method processes all documents to find related question papers
        and mark schemes based on unit numbers and metadata.
        
        Returns:
            int: Number of relationships found
        """
        relationship_count = 0
        
        # First ensure all documents have unit numbers
        self.update_unit_numbers()
        
        # Then find relationships
        for doc in self.index["documents"]:
            # Find related documents based on pattern matching
            self._update_related_documents(doc["id"])
            
            # Find related documents based on unit numbers
            related = self.find_related_by_unit(doc["id"])
            relationship_count += len(related)
        
        return relationship_count

    def get_unit_distribution(self) -> Dict[int, int]:
        """
        Get distribution of documents by unit number.
        
        Returns:
            Dict[int, int]: Dictionary with unit numbers as keys and document counts as values
        """
        unit_counts = {}
        for doc in self.index["documents"]:
            if doc.get("unit_number") is not None:
                unit_number = doc["unit_number"]
                unit_counts[unit_number] = unit_counts.get(unit_number, 0) + 1
        
        return unit_counts
        
    def get_documents_without_unit(self) -> List[str]:
        """
        Get list of documents without a unit number.
        
        Returns:
            List[str]: List of document IDs without a unit number
        """
        return [doc["id"] for doc in self.index["documents"] 
                if "unit_number" not in doc or doc["unit_number"] is None]

    # Hierarchical transformation methods
    
    def transform_to_hierarchical(self, 
                                output_path: str = "hierarchical_index.json", 
                                interactive: bool = False) -> Dict[str, Any]:
        """
        Transform the flat index into a hierarchical structure.
        
        Args:
            output_path: Path where the new hierarchical index will be saved
            interactive: Whether to prompt user for conflict resolution
            
        Returns:
            Dict: The new hierarchical structure
        """
        print(f"Transforming index with {len(self.index['documents'])} documents...")
        
        # Ensure all documents have unit numbers and relationships
        self.update_all_document_relations()
        
        # Reset hierarchical structure
        self.hierarchical_structure = {"subjects": {}}
        self.document_mapping = {}
        
        # Group documents by subject, year, qualification, and unit
        grouped_docs = self._group_documents()
        
        # Build the hierarchical structure
        self._build_hierarchy(grouped_docs)
        
        # Validate the transformation
        self._validate_transformation()
        
        # Save the new structure
        output_path = Path(output_path)
        try:
            # Create parent directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.hierarchical_structure, f, indent=2, ensure_ascii=False)
            print(f"New hierarchical structure saved to {output_path}")
        except Exception as e:
            print(f"Error saving structure: {str(e)}")
        
        return self.hierarchical_structure
    
    def _group_documents(self) -> Dict:
        """
        Group documents by subject, year, qualification, and unit number.
        
        Returns:
            Dict: Nested dictionary with grouped documents
        """
        grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))
        
        for doc in self.index["documents"]:
            # Skip documents without essential metadata
            if not all(key in doc for key in ["subject", "year", "qualification", "unit_number"]):
                continue
                
            subject = doc["subject"]
            year = doc["year"]
            qualification = doc["qualification"]
            unit_number = doc["unit_number"]
            
            # Add document to the appropriate group
            grouped[subject][year][qualification][unit_number].append(doc)
            
        return grouped
    
    def _build_hierarchy(self, grouped_docs: Dict) -> None:
        """
        Build the hierarchical structure from grouped documents.
        
        Args:
            grouped_docs: Documents grouped by subject, year, qualification, and unit
        """
        for subject, years in grouped_docs.items():
            self.hierarchical_structure["subjects"][subject] = {"years": {}}
            
            for year, qualifications in years.items():
                self.hierarchical_structure["subjects"][subject]["years"][str(year)] = {"qualifications": {}}
                
                for qualification, units in qualifications.items():
                    self.hierarchical_structure["subjects"][subject]["years"][str(year)]["qualifications"][qualification] = {"exams": {}}
                    
                    for unit_number, docs in units.items():
                        # Create exam unit entry if it doesn't exist
                        unit_key = f"Unit {unit_number}"
                        
                        if unit_key not in self.hierarchical_structure["subjects"][subject]["years"][str(year)]["qualifications"][qualification]["exams"]:
                            self.hierarchical_structure["subjects"][subject]["years"][str(year)]["qualifications"][qualification]["exams"][unit_key] = {
                                "unit_number": unit_number,
                                "documents": {}
                            }
                        
                        # Now merge documents into this exam unit
                        self._merge_documents_into_exam(
                            docs, 
                            self.hierarchical_structure["subjects"][subject]["years"][str(year)]["qualifications"][qualification]["exams"][unit_key]
                        )
    
    def _merge_documents_into_exam(self, documents: List[Dict[str, Any]], exam_entry: Dict[str, Any]) -> None:
        """
        Merge documents into an exam entry, handling metadata conflicts.
        
        Args:
            documents: List of documents for this exam unit
            exam_entry: The exam entry to merge into
        """
        # First, extract common metadata fields to merge at exam level
        exam_level_metadata = {
            "name": None,
            "exam_season": None,
            "exam_length": None,
            "total_marks": None,
            "instructions_for_candidates": None,
            "instructions_for_examiners": None
        }
        
        # Find conflicting metadata values
        conflicts = {}
        for field in exam_level_metadata:
            values = set()
            sources = {}
            
            for doc in documents:
                if field in doc and doc[field] is not None:
                    values.add(doc[field])
                    if doc[field] not in sources:
                        sources[doc[field]] = []
                    sources[doc[field]].append(doc["id"])
                
                # Special case for exam paper name
                if field == "name" and "exam_paper" in doc:
                    values.add(doc["exam_paper"])
                    if doc["exam_paper"] not in sources:
                        sources[doc["exam_paper"]] = []
                    sources[doc["exam_paper"]].append(doc["id"])
            
            # If multiple values exist, we have a conflict
            if len(values) > 1:
                conflicts[field] = {"values": list(values), "sources": sources}
            elif len(values) == 1:
                exam_level_metadata[field] = list(values)[0]
        
        # Resolve conflicts if any
        if conflicts:
            self._resolve_conflicts(conflicts, exam_level_metadata, interactive=False)
        
        # Update exam entry with merged metadata
        for field, value in exam_level_metadata.items():
            if value is not None:
                exam_entry[field] = value
                
        # If name wasn't set and unit_number is available, set a default name
        if "name" not in exam_entry or exam_entry["name"] is None:
            exam_entry["name"] = f"Unit {exam_entry['unit_number']}"
            
        # Add each document to the appropriate collection
        for doc in documents:
            # Create a simplified document entry
            doc_entry = {
                "id": doc["id"],
                "content_path": doc["content_path"],
                "metadata_path": doc["metadata_path"]
            }
            
            # Add document to the appropriate collection
            doc_type = doc.get("type", "Unknown")
            if doc_type not in exam_entry["documents"]:
                exam_entry["documents"][doc_type] = []
                
            exam_entry["documents"][doc_type].append(doc_entry)
            
            # Update document mapping for validation
            self.document_mapping[doc["id"]] = {
                "subject": doc.get("subject"),
                "year": doc.get("year"),
                "qualification": doc.get("qualification"),
                "unit": exam_entry["name"]
            }
    
    def _resolve_conflicts(self, conflicts: Dict[str, Dict], exam_level_metadata: Dict[str, Any], 
                         interactive: bool = False) -> None:
        """
        Resolve metadata conflicts, either interactively or by taking the first value.
        
        Args:
            conflicts: Dictionary of conflicting fields and their values
            exam_level_metadata: Dictionary to update with resolved values
            interactive: Whether to prompt user for conflict resolution
        """
        if not interactive:
            # In non-interactive mode, just pick the first value
            for field, conflict_data in conflicts.items():
                exam_level_metadata[field] = conflict_data["values"][0]
            return
            
        print("\nResolving metadata conflicts for an exam unit:")
        
        for field, conflict_data in conflicts.items():
            print(f"\nField: {field}")
            print("Conflicting values:")
            
            for i, value in enumerate(conflict_data["values"]):
                sources = conflict_data["sources"][value]
                source_str = ", ".join(sources[:2])
                if len(sources) > 2:
                    source_str += f" and {len(sources) - 2} more"
                print(f"{i+1}. '{value}' (from: {source_str})")
            
            print(f"{len(conflict_data['values'])+1}. Enter a custom value")
            
            while True:
                try:
                    choice = int(input(f"Choose value for {field} (1-{len(conflict_data['values'])+1}): "))
                    if 1 <= choice <= len(conflict_data["values"]):
                        exam_level_metadata[field] = conflict_data["values"][choice-1]
                        break
                    elif choice == len(conflict_data["values"])+1:
                        custom = input(f"Enter custom value for {field}: ")
                        exam_level_metadata[field] = custom
                        break
                    else:
                        print("Invalid choice")
                except ValueError:
                    print("Please enter a number")
    
    def _validate_transformation(self) -> bool:
        """
        Validate that all original documents are included in the new structure.
        
        Returns:
            bool: True if validation passes, False otherwise
        """
        original_ids = {doc["id"] for doc in self.index["documents"]}
        transformed_ids = set(self.document_mapping.keys())
        
        missing_ids = original_ids - transformed_ids
        if missing_ids:
            print(f"Warning: {len(missing_ids)} documents were not included in the transformed structure:")
            for doc_id in list(missing_ids)[:10]:
                print(f"  - {doc_id}")
            if len(missing_ids) > 10:
                print(f"  - ... and {len(missing_ids) - 10} more")
            return False
        
        print(f"Validation successful: All {len(original_ids)} documents included in the new structure")
        return True
    
    # Methods for enhancing hierarchical structure with metadata
    def enhance_hierarchical_structure(self, 
                                     hierarchical_path: str = "hierarchical_index.json",
                                     interactive: bool = False) -> Dict[str, Any]:
        """
        Enhance a hierarchical structure with metadata from document files.
        
        Args:
            hierarchical_path: Path to the hierarchical structure file
            interactive: Whether to prompt user for conflict resolution
            
        Returns:
            Dict: The enhanced hierarchical structure
        """
        # Load the hierarchical structure
        try:
            with open(hierarchical_path, 'r', encoding='utf-8') as f:
                self.hierarchical_structure = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error: Could not load structure from {hierarchical_path}: {str(e)}")
            return {}
            
        print("Enhancing hierarchical structure with document metadata...")
        
        # Map of metadata fields from files to our standardized field names
        metadata_field_mapping = {
            "Exam Length": "exam_length",
            "Total Marks": "total_marks", 
            "Information for Candidates": "instructions_for_candidates",
            "Information for Examiners": "instructions_for_examiners"
        }
        
        # Track statistics
        stats = {
            "processed_documents": 0,
            "metadata_files_found": 0,
            "metadata_files_missing": 0,
            "metadata_fields_added": 0,
            "conflict_resolutions": 0
        }
        
        # Traverse the hierarchical structure to find all documents
        self._process_hierarchical_structure(stats, metadata_field_mapping, interactive)
        
        print(f"Metadata enhancement complete:")
        print(f"- Processed {stats['processed_documents']} documents")
        print(f"- Found {stats['metadata_files_found']} metadata files")
        print(f"- Added {stats['metadata_fields_added']} metadata fields to exams")
        print(f"- Resolved {stats['conflict_resolutions']} metadata conflicts")
        if stats["metadata_files_missing"] > 0:
            print(f"- Warning: {stats['metadata_files_missing']} metadata files were missing")
        
        # Save the enhanced structure
        with open(hierarchical_path, 'w', encoding='utf-8') as f:
            json.dump(self.hierarchical_structure, f, indent=2, ensure_ascii=False)
        
        return self.hierarchical_structure
    
    def _process_hierarchical_structure(self, stats: Dict[str, int], metadata_field_mapping: Dict[str, str], 
                                      interactive: bool) -> None:
        """
        Process the entire hierarchical structure to enhance with metadata.
        
        Args:
            stats: Dictionary to track statistics
            metadata_field_mapping: Mapping of file fields to structure fields
            interactive: Whether to prompt user for conflict resolution
        """
        for subject_name, subject in self.hierarchical_structure["subjects"].items():
            for year_name, year in subject["years"].items():
                for qual_name, qual in year["qualifications"].items():
                    for exam_name, exam in qual["exams"].items():
                        # Dictionary to collect exam-level metadata from all documents
                        collected_metadata = defaultdict(lambda: defaultdict(list))
                        
                        # Process each document for this exam
                        for doc_type, documents in exam["documents"].items():
                            for doc in documents:
                                stats["processed_documents"] += 1
                                
                                # Read the document metadata file
                                metadata = self._read_metadata_file(doc["metadata_path"])
                                if metadata:
                                    stats["metadata_files_found"] += 1
                                    
                                    # Collect metadata fields 
                                    for file_field, struct_field in metadata_field_mapping.items():
                                        if file_field in metadata:
                                            value = metadata[file_field]
                                            collected_metadata[struct_field][value].append(doc["id"])
                                else:
                                    stats["metadata_files_missing"] += 1
                        
                        # Merge collected metadata into exam entry
                        stats["metadata_fields_added"] += self._merge_collected_metadata(
                            collected_metadata, 
                            exam,
                            metadata_field_mapping.values(),
                            interactive,
                            stats
                        )
    
    def _read_metadata_file(self, metadata_path: str) -> Optional[Dict[str, Any]]:
        """
        Read a document metadata file.
        
        Args:
            metadata_path: Path to the metadata file
            
        Returns:
            Dict or None: The parsed metadata, or None if file doesn't exist/can't be parsed
        """
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, PermissionError) as e:
            # Print a warning but continue processing
            return None
    
    def _merge_collected_metadata(self, 
                                collected_metadata: Dict[str, Dict[Any, List[str]]],
                                exam_entry: Dict[str, Any],
                                metadata_fields: List[str],
                                interactive: bool,
                                stats: Dict[str, int]) -> int:
        """
        Merge collected metadata into an exam entry, resolving conflicts if necessary.
        
        Args:
            collected_metadata: Dictionary of collected metadata values by field
            exam_entry: The exam entry to update with metadata
            metadata_fields: List of metadata field names to process
            interactive: Whether to prompt user for conflict resolution
            stats: Dictionary to track statistics
            
        Returns:
            int: Number of metadata fields added or updated
        """
        fields_updated = 0
        
        for field in metadata_fields:
            if field in collected_metadata and collected_metadata[field]:
                # If only one value exists for this field, use it
                if len(collected_metadata[field]) == 1:
                    value = next(iter(collected_metadata[field].keys()))
                    exam_entry[field] = value
                    fields_updated += 1
                    
                # If multiple values exist, handle the conflict
                elif len(collected_metadata[field]) > 1:
                    stats["conflict_resolutions"] += 1
                    values = list(collected_metadata[field].keys())
                    
                    # Handle interactive conflict resolution if enabled
                    if interactive:
                        resolved_value = self._resolve_metadata_conflict_interactive(
                            field, values, collected_metadata[field], exam_entry)
                        if resolved_value is not None:
                            exam_entry[field] = resolved_value
                            fields_updated += 1
                    else:
                        # In non-interactive mode, just take the first value
                        exam_entry[field] = values[0]
                        fields_updated += 1
        
        return fields_updated
    
    def _resolve_metadata_conflict_interactive(self, field: str, values: List[Any], 
                                            value_sources: Dict[Any, List[str]],
                                            exam_entry: Dict[str, Any]) -> Optional[Any]:
        """
        Interactively resolve metadata conflicts by prompting the user.
        
        Args:
            field: The metadata field with conflicts
            values: List of conflicting values
            value_sources: Dictionary mapping values to document IDs they came from
            exam_entry: The exam entry being processed
            
        Returns:
            Any or None: The resolved value, or None if resolution failed
        """
        print(f"\nConflict in {field} for exam {exam_entry.get('name', 'Unknown')}:")
        for i, value in enumerate(values):
            doc_ids = value_sources[value]
            doc_str = ", ".join(doc_ids[:2])
            if len(doc_ids) > 2:
                doc_str += f" and {len(doc_ids) - 2} more"
            print(f"{i+1}. '{value}' (from documents: {doc_str})")
        print(f"{len(values)+1}. Enter custom value")
        
        while True:
            try:
                choice = int(input(f"Choose value for {field} (1-{len(values)+1}): "))
                if 1 <= choice <= len(values):
                    return values[choice-1]
                elif choice == len(values)+1:
                    return input(f"Enter custom value: ")
                else:
                    print("Invalid choice")
            except ValueError:
                print("Please enter a number")
        
        return None

    # Combined workflow methods
    def run_full_process(self, 
                       output_path: str = "hierarchical_index.json", 
                       interactive: bool = False) -> Dict[str, Any]:
        """
        Run the full index processing workflow: update, sort, transform, and enhance.
        
        Args:
            output_path: Path for the output hierarchical structure
            interactive: Whether to prompt user for conflict resolution
            
        Returns:
            Dict: The final hierarchical structure
        """
        print(f"Processing {len(self.index['documents'])} documents...")
        
        # Step 1: Update unit numbers
        updated_count = self.update_unit_numbers()
        print(f"Added unit numbers to {updated_count} documents")
        
        # Step 2: Sort the index
        self.sort_index()
        print(f"Index sorted by subject, year, qualification, and unit number")
        
        # Step 3: Update document relationships
        relationship_count = self.update_all_document_relations()
        print(f"Found {relationship_count} relationships between documents")
        
        # Step 4: Save the updated flat index
        self.save_index()
        print(f"Updated index saved to {self.index_path}")
        
        # Step 5: Transform to hierarchical structure
        structure = self.transform_to_hierarchical(output_path, interactive)
        
        # Step 6: Enhance the hierarchical structure with metadata
        structure = self.enhance_hierarchical_structure(output_path, interactive)
        
        # Print summary statistics
        unit_distribution = self.get_unit_distribution()
        print("\nDistribution of documents by unit number:")
        for unit, count in sorted(unit_distribution.items()):
            print(f"Unit {unit}: {count} documents")
        
        null_units = self.get_documents_without_unit()
        if null_units:
            print(f"\nWarning: {len(null_units)} documents have no unit number:")
            for doc_id in null_units[:10]:  # Show only first 10
                print(f"  - {doc_id}")
            if len(null_units) > 10:
                print(f"  - ... and {len(null_units) - 10} more")
        
        return structure