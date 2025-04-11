"""
Transform flat document index into a hierarchical structure organized by
subject, year, qualification, and exam unit.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Set, Optional, Tuple
from collections import defaultdict

class IndexStructureTransformer:
    """
    Transforms flat document index into a hierarchical structure.
    
    This class groups related documents (question papers and mark schemes) under their
    respective exam units, merging common metadata while preserving document-specific details.
    """
    
    def __init__(self, 
                 index_manager, 
                 output_path: str = "Index/hierarchical_index.json",
                 interactive: bool = True):
        """
        Initialize the transformer with an existing index manager.
        
        Args:
            index_manager: Existing index manager with flat document structure
            output_path: Path where the new hierarchical index will be saved
            interactive: Whether to prompt user for conflict resolution
        """
        self.index_manager = index_manager
        self.output_path = Path(output_path)
        self.interactive = interactive
        self.new_structure = {"subjects": {}}
        self.document_mapping = {}  # Maps original document IDs to their new location
        
    def transform(self) -> Dict[str, Any]:
        """
        Transform the flat index into a hierarchical structure.
        
        Returns:
            Dict: The new hierarchical structure
        """
        # Ensure all documents have unit numbers and relationships are established
        self.index_manager.update_all_document_relations()
        
        # Group documents by subject, year, qualification, and unit
        grouped_docs = self._group_documents()
        
        # Build the hierarchical structure
        self._build_hierarchy(grouped_docs)
        
        # Validate the transformation
        self._validate_transformation()
        
        # Save the new structure
        if not self._save_new_structure():
            print("Failed to save the new structure.")
        
        return self.new_structure

    def _group_documents(self) -> Dict[str, Dict[int, Dict[str, Dict[int, List[Dict[str, Any]]]]]]:
        """
        Group documents by subject, year, qualification, and unit number.
        
        Returns:
            Dict: Nested dictionary with grouped documents
        """
        grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))
        
        for doc in self.index_manager.index["documents"]:
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
            self.new_structure["subjects"][subject] = {"years": {}}
            
            for year, qualifications in years.items():
                self.new_structure["subjects"][subject]["years"][str(year)] = {"qualifications": {}}
                
                for qualification, units in qualifications.items():
                    self.new_structure["subjects"][subject]["years"][str(year)]["qualifications"][qualification] = {"exams": {}}
                    
                    for unit_number, docs in units.items():
                        # Create exam unit entry if it doesn't exist
                        unit_key = f"Unit {unit_number}"
                        
                        if unit_key not in self.new_structure["subjects"][subject]["years"][str(year)]["qualifications"][qualification]["exams"]:
                            self.new_structure["subjects"][subject]["years"][str(year)]["qualifications"][qualification]["exams"][unit_key] = {
                                "unit_number": unit_number,
                                "documents": {}
                            }
                        
                        # Now merge documents into this exam unit
                        self._merge_documents_into_exam(
                            docs, 
                            self.new_structure["subjects"][subject]["years"][str(year)]["qualifications"][qualification]["exams"][unit_key]
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
        if conflicts and self.interactive:
            self._resolve_conflicts(conflicts, exam_level_metadata)
        elif conflicts:
            # In non-interactive mode, just pick the first value
            for field, conflict_data in conflicts.items():
                exam_level_metadata[field] = conflict_data["values"][0]
        
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
    
    def _resolve_conflicts(self, conflicts: Dict[str, Dict], exam_level_metadata: Dict[str, Any]) -> None:
        """
        Prompt user to resolve metadata conflicts.
        
        Args:
            conflicts: Dictionary of conflicting fields and their values
            exam_level_metadata: Dictionary to update with resolved values
        """
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
        original_ids = {doc["id"] for doc in self.index_manager.index["documents"]}
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
    
    def _save_new_structure(self) -> bool:
        """
        Save the new hierarchical structure to a file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create parent directory if it doesn't exist
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(self.new_structure, f, indent=2, ensure_ascii=False)
            print(f"New hierarchical structure saved to {self.output_path}")
            return True
        except Exception as e:
            print(f"Error saving structure: {str(e)}")
            return False
    
    def enhance_with_document_metadata(self) -> Dict[str, Any]:
        """
        Enhance the hierarchical structure with metadata from individual document files.
        
        This method reads metadata files for each document in the structure and
        merges relevant exam-level information like exam length, total marks, etc.
        
        Returns:
            Dict: The enhanced hierarchical structure
        """
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
        for subject_name, subject in self.new_structure["subjects"].items():
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
                            metadata_field_mapping.values()
                        )
        
        print(f"Metadata enhancement complete:")
        print(f"- Processed {stats['processed_documents']} documents")
        print(f"- Found {stats['metadata_files_found']} metadata files")
        print(f"- Added {stats['metadata_fields_added']} metadata fields to exams")
        print(f"- Resolved {stats['conflict_resolutions']} metadata conflicts")
        if stats["metadata_files_missing"] > 0:
            print(f"- Warning: {stats['metadata_files_missing']} metadata files were missing")
        
        # Save the enhanced structure
        self._save_new_structure()
        
        return self.new_structure
    
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
            print(f"Warning: Could not read metadata file {metadata_path}: {str(e)}")
            return None
    
    def _merge_collected_metadata(self, 
                                collected_metadata: Dict[str, Dict[Any, List[str]]],
                                exam_entry: Dict[str, Any],
                                metadata_fields: List[str]) -> int:
        """
        Merge collected metadata into an exam entry, resolving conflicts if necessary.
        
        Args:
            collected_metadata: Dictionary of collected metadata values by field
            exam_entry: The exam entry to update with metadata
            metadata_fields: List of metadata field names to process
            
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
                    values = list(collected_metadata[field].keys())
                    resolved_value = None
                    
                    # If interactive, prompt user to resolve conflict
                    if self.interactive:
                        print(f"\nConflict in {field} for exam {exam_entry.get('name', 'Unknown')}:")
                        for i, value in enumerate(values):
                            doc_ids = collected_metadata[field][value]
                            doc_str = ", ".join(doc_ids[:2])
                            if len(doc_ids) > 2:
                                doc_str += f" and {len(doc_ids) - 2} more"
                            print(f"{i+1}. '{value}' (from documents: {doc_str})")
                        print(f"{len(values)+1}. Enter custom value")
                        
                        while True:
                            try:
                                choice = int(input(f"Choose value for {field} (1-{len(values)+1}): "))
                                if 1 <= choice <= len(values):
                                    resolved_value = values[choice-1]
                                    break
                                elif choice == len(values)+1:
                                    custom = input(f"Enter custom value: ")
                                    resolved_value = custom
                                    break
                                else:
                                    print("Invalid choice")
                            except ValueError:
                                print("Please enter a number")
                    else:
                        # In non-interactive mode, just take the first value
                        resolved_value = values[0]
                    
                    if resolved_value is not None:
                        exam_entry[field] = resolved_value
                        fields_updated += 1
                    
        return fields_updated