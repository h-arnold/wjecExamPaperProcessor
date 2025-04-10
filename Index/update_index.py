"""
Utility script to update the index.json file with missing exam_season field.
Can also move/copy index and related files to a different directory.
"""

import json
import re
import os
import shutil
from pathlib import Path


def infer_exam_season(document_id, year):
    """
    Infer exam season from document ID or other metadata.
    
    Args:
        document_id (str): Document ID
        year (int): Exam year
        
    Returns:
        str: Inferred exam season ("Summer", "Winter", or "Unknown")
    """
    # Check for common season indicators in ID
    document_id = document_id.lower()
    
    if document_id.startswith('s') or 's' + str(year)[-2:] in document_id:
        return "Summer"
    elif document_id.startswith('w') or 'w' + str(year)[-2:] in document_id:
        return "Winter"
    
    # Check date patterns in the document ID (DDMMYY format)
    date_match = re.search(r'(\d{2})(\d{2})(\d{2})', document_id)
    if date_match:
        month = int(date_match.group(2))
        if 5 <= month <= 8:  # May to August
            return "Summer"
        elif month >= 11 or month <= 2:  # November to February
            return "Winter"
    
    # Check MS filename patterns including season indicators
    if "summer" in document_id or "s" in document_id:
        return "Summer"
    if "winter" in document_id or "w" in document_id:
        return "Winter"
    
    return "Unknown"


def get_exam_season_from_metadata(metadata_path):
    """
    Extract exam season directly from a metadata file.
    
    Args:
        metadata_path (str): Path to metadata file
        
    Returns:
        str or None: The exam season if found, None otherwise
    """
    if not metadata_path or not Path(metadata_path).exists():
        return None
    
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            
        # Check for exam season in metadata
        if "Exam Season" in metadata and metadata["Exam Season"]:
            return metadata["Exam Season"]
        
        return None
    except (json.JSONDecodeError, IOError, FileNotFoundError):
        # Return None if file doesn't exist or can't be parsed
        return None


def copy_file_with_dirs(src_path, target_dir, relative_path=None):
    """
    Copy a file to a target directory, creating any necessary subdirectories.
    
    Args:
        src_path (str or Path): Source file path
        target_dir (str or Path): Target base directory
        relative_path (str or Path, optional): Relative path within target directory
            
    Returns:
        Path: Path to the copied file, or None if copy failed
    """
    src_path = Path(src_path)
    if not src_path.exists():
        print(f"Warning: Source file not found: {src_path}")
        return None
        
    if relative_path:
        # If relative path provided, use it
        dest_path = Path(target_dir) / relative_path
    else:
        # Otherwise just use the filename
        dest_path = Path(target_dir) / src_path.name
        
    # Create parent directories if they don't exist
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        shutil.copy2(src_path, dest_path)
        return dest_path
    except Exception as e:
        print(f"Error copying {src_path} to {dest_path}: {str(e)}")
        return None


def update_paths_in_index(index_data, source_base, target_base):
    """
    Update paths in index to point to the new target directory.
    
    Args:
        index_data (dict): The index dictionary
        source_base (str or Path): Original base directory
        target_base (str or Path): New target base directory
            
    Returns:
        dict: Updated index with new paths
    """
    source_base = Path(source_base)
    target_base = Path(target_base)
    
    # Track files to be moved
    files_to_move = []
    
    # Update paths in the index
    for doc in index_data.get("documents", []):
        for path_key in ["content_path", "metadata_path"]:
            if path_key in doc and doc[path_key]:
                old_path = Path(doc[path_key])
                
                # Try to make path relative to source_base
                try:
                    rel_path = old_path.relative_to(source_base)
                except ValueError:
                    # If not under source_base, keep as is
                    rel_path = old_path
                
                # Set new path in index
                new_path = target_base / rel_path
                doc[path_key] = str(new_path)
                
                # Add to list of files to move
                files_to_move.append((old_path, new_path))
    
    return index_data, files_to_move


def move_files_to_target(files_to_move, move=False):
    """
    Copy or move files to their target locations.
    
    Args:
        files_to_move (list): List of (source, target) file path tuples
        move (bool): True to move files, False to copy them
            
    Returns:
        int: Number of files successfully processed
    """
    success_count = 0
    
    for src_path, dest_path in files_to_move:
        # Create parent directories if they don't exist
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if src_path.exists():
                if move:
                    shutil.move(str(src_path), str(dest_path))
                else:
                    shutil.copy2(str(src_path), str(dest_path))
                success_count += 1
            else:
                print(f"Warning: Source file not found: {src_path}")
        except Exception as e:
            print(f"Error {'moving' if move else 'copying'} {src_path} to {dest_path}: {str(e)}")
    
    return success_count


def update_index_with_exam_season(index_path="test_index.json", target_dir=None, move_files=False):
    """
    Update the index.json file by adding the exam_season field to all documents.
    Optionally move/copy the index and related files to a target directory.
    
    Args:
        index_path (str): Path to the index file
        target_dir (str, optional): Target directory for index and related files
        move_files (bool): True to move files, False to copy them
        
    Returns:
        dict: The updated index dictionary
    """
    index_path = Path(index_path)
    
    if not index_path.exists():
        print(f"Error: Index file not found at {index_path}")
        return None
    
    try:
        # Load the index file
        with open(index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)
        
        print(f"Loaded index with {len(index.get('documents', []))} documents")
        
        # Count documents without exam_season
        missing_count = 0
        from_metadata_count = 0
        from_inference_count = 0
        
        # Update each document
        for doc in index.get("documents", []):
            if "exam_season" not in doc or not doc["exam_season"]:
                missing_count += 1
                
                # First try to get exam season from metadata file
                metadata_path = doc.get("metadata_path")
                exam_season = get_exam_season_from_metadata(metadata_path)
                
                if exam_season:
                    doc["exam_season"] = exam_season
                    from_metadata_count += 1
                    print(f"Retrieved exam season '{exam_season}' from metadata for {doc['id']}")
                else:
                    # Fall back to inference if metadata doesn't have it
                    doc["exam_season"] = infer_exam_season(doc["id"], doc.get("year", 0))
                    from_inference_count += 1
                    print(f"Inferred exam season '{doc['exam_season']}' for {doc['id']}")
        
        print(f"Updated {missing_count} documents with missing exam_season field")
        print(f"- {from_metadata_count} updated from metadata files")
        print(f"- {from_inference_count} inferred from document IDs")
        
        # If target directory is specified, update paths and move/copy files
        if target_dir:
            target_dir = Path(target_dir)
            source_dir = index_path.parent
            
            print(f"Moving/copying files to target directory: {target_dir}")
            
            # Update paths in index
            index, files_to_move = update_paths_in_index(index, source_dir, target_dir)
            
            # Create target directory if it doesn't exist
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Move or copy files
            action_word = "Moving" if move_files else "Copying"
            print(f"{action_word} {len(files_to_move)} files to target directory...")
            success_count = move_files_to_target(files_to_move, move=move_files)
            print(f"Successfully {action_word.lower()} {success_count} of {len(files_to_move)} files")
            
            # Save index to target directory
            target_index_path = target_dir / index_path.name
            with open(target_index_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
            print(f"Saved index to {target_index_path}")
            
            # If moving, remove original index if it's different from target
            if move_files and str(index_path) != str(target_index_path):
                index_path.unlink()
                print(f"Removed original index at {index_path}")
            
            return index
        else:
            # Save the updated index to original location
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
            
            print(f"Successfully updated index file at {index_path}")
            return index
        
    except Exception as e:
        print(f"Error updating index: {str(e)}")
        return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Update index.json with exam_season field and optionally move/copy files')
    parser.add_argument('--index', default='test_index.json', help='Path to the index file')
    parser.add_argument('--target-dir', default = 'Index', help='Target directory for index and related files')
    parser.add_argument('--move', action='store_true', help='Move files instead of copying them')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show verbose output')
    
    args = parser.parse_args()
    update_index_with_exam_season(args.index, args.target_dir, args.move)
