#!/usr/bin/env python3
"""
Combine decrypted metadata.json files from Apple Generative Model safety overrides.

This script processes all metadata.json files in the decrypted_overrides directory
and combines them into single files for each region/locale, plus a global file.
Entries are deduplicated to provide clean combined lists.
"""

import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Union, Any


def merge_metadata(metadata_list: List[Dict]) -> Dict:
    """
    Merge multiple metadata dictionaries, deduplicating entries.
    
    Args:
        metadata_list: List of metadata dictionaries to merge
        
    Returns:
        Merged metadata dictionary with deduplicated entries
    """
    merged = {
        "reject": set(),
        "remove": set(),
        "replace": {},
        "regexReject": set(),
        "regexRemove": set(),
        "regexReplace": {}
    }
    
    for metadata in metadata_list:
        # Add list entries to sets (automatic deduplication)
        merged["reject"].update(metadata.get("reject", []))
        merged["remove"].update(metadata.get("remove", []))
        merged["regexReject"].update(metadata.get("regexReject", []))
        merged["regexRemove"].update(metadata.get("regexRemove", []))
        
        # Merge replace dictionaries
        merged["replace"].update(metadata.get("replace", {}))
        merged["regexReplace"].update(metadata.get("regexReplace", {}))
    
    # Convert sets back to sorted lists for consistent output
    result = {
        "reject": sorted(list(merged["reject"])),
        "remove": sorted(list(merged["remove"])),
        "replace": dict(sorted(merged["replace"].items())),
        "regexReject": sorted(list(merged["regexReject"])),
        "regexRemove": sorted(list(merged["regexRemove"])),
        "regexReplace": dict(sorted(merged["regexReplace"].items()))
    }
    
    return result


def find_metadata_files(decrypted_dir: str) -> Dict[str, Any]:
    """
    Find all metadata.json files and categorize them by type.
    
    Args:
        decrypted_dir: Path to the decrypted_overrides directory
        
    Returns:
        Dictionary with categories as keys and lists of file paths as values
    """
    files = {
        "global": [],
        "regions": defaultdict(list),
        "locales": defaultdict(list)
    }
    
    # Walk through all directories
    for root, dirs, filenames in os.walk(decrypted_dir):
        if "metadata.json" in filenames:
            metadata_path = os.path.join(root, "metadata.json")
            
            # Check if this is a region-specific file
            if "/region/" in metadata_path:
                region_match = re.search(r'/region/([^/]+)/', metadata_path)
                if region_match:
                    region = region_match.group(1)
                    files["regions"][region].append(metadata_path)
            
            # Check if this is a locale-specific file  
            elif "/locale/" in metadata_path:
                locale_match = re.search(r'/locale/([^/]+)/', metadata_path)
                if locale_match:
                    locale = locale_match.group(1)
                    files["locales"][locale].append(metadata_path)
            
            # Check if this is a global file (directly in AssetData/)
            elif metadata_path.endswith("/AssetData/metadata.json"):
                files["global"].append(metadata_path)
    
    return files


def load_metadata_file(filepath: str) -> Dict:
    """
    Load a metadata.json file and return its contents.
    
    Args:
        filepath: Path to the metadata.json file
        
    Returns:
        Dictionary containing the metadata
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Warning: Could not load {filepath}: {e}")
        return {}


def combine_files(file_list: List[str]) -> Dict:
    """
    Combine multiple metadata files into a single merged dictionary.
    
    Args:
        file_list: List of file paths to combine
        
    Returns:
        Merged metadata dictionary
    """
    metadata_list = []
    for filepath in file_list:
        metadata = load_metadata_file(filepath)
        if metadata:  # Only add non-empty metadata
            metadata_list.append(metadata)
    
    return merge_metadata(metadata_list)


def save_combined_file(data: Dict, output_path: str) -> None:
    """
    Save combined metadata to a JSON file.
    
    Args:
        data: Dictionary to save
        output_path: Path where to save the file
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved combined metadata to {output_path}")


def main():
    """Main function to process all metadata files."""
    decrypted_dir = "decrypted_overrides"
    output_dir = "combined_metadata"
    
    if not os.path.exists(decrypted_dir):
        print(f"Error: Directory {decrypted_dir} does not exist.")
        return
    
    print(f"Processing metadata files in {decrypted_dir}...")
    
    # Find all metadata files
    files = find_metadata_files(decrypted_dir)
    
    # Process global files
    print(f"Found {len(files['global'])} global metadata files")
    if files['global']:
        global_data = combine_files(files['global'])
        save_combined_file(global_data, f"{output_dir}/global_metadata.json")
        print(f"  - Global: {len(global_data['reject'])} reject, {len(global_data['regexReject'])} regexReject entries")
    
    # Process region-specific files
    print(f"Found {len(files['regions'])} regions")
    for region, file_list in files['regions'].items():
        print(f"  Processing region {region}: {len(file_list)} files")
        region_data = combine_files(file_list)
        save_combined_file(region_data, f"{output_dir}/region_{region}_metadata.json")
        print(f"    - Region {region}: {len(region_data['reject'])} reject, {len(region_data['regexReject'])} regexReject entries")
    
    # Process locale-specific files
    print(f"Found {len(files['locales'])} locales")
    for locale, file_list in files['locales'].items():
        print(f"  Processing locale {locale}: {len(file_list)} files")
        locale_data = combine_files(file_list)
        save_combined_file(locale_data, f"{output_dir}/locale_{locale}_metadata.json")
        print(f"    - Locale {locale}: {len(locale_data['reject'])} reject, {len(locale_data['regexReject'])} regexReject entries")
    
    print(f"\nCombined metadata files saved to {output_dir}/")
    print("These files provide a convenient way to review all safety filters by region/locale.")


if __name__ == "__main__":
    main()