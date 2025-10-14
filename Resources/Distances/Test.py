import json
import os
import unicodedata
from pathlib import Path

DISCREPANCY_THRESHOLD_KM = 14


def normalize_name_to_filename(location_name):
    """
    Converts a location name into a standardized filename.
    Example: "municipiul Bender (Tighina)" -> "Municipiul-Bender-Tighina.json"
    """
    # Normalize Unicode characters (like Chișinău -> Chisinau)
    # This makes the script more robust if filenames don't have diacritics.
    normalized = unicodedata.normalize('NFKD', location_name).encode('ASCII', 'ignore').decode('utf-8')

    # Replace spaces and parentheses with hyphens, remove trailing hyphens
    sanitized = normalized.replace(" ", "-").replace("(", "").replace(")", "")

    # Handle case variations by checking for different casings
    potential_filenames = [
        f"{sanitized}.json",
        f"{sanitized.lower()}.json",
        f"{location_name.replace(' ', '-')}.json" # Try with original diacritics
    ]

    for filename in potential_filenames:
        if os.path.exists(filename):
            return filename

    # If no file was found after trying variations, return the most likely name
    return f"{location_name.replace(' ', '-')}.json"


def check_distances():
    """
    Main function to scan all JSON files in the current directory and check distance consistency.
    Reports only discrepancies exceeding DISCREPANCY_THRESHOLD_KM.
    """
    # Collect all JSON files in current directory
    json_files = [f for f in os.listdir('.') if f.endswith('.json') and f != '_manifest.json']
    
    if not json_files:
        print("No JSON files found in the current directory.")
        return
    
    # Track all large discrepancies across all files
    large_discrepancies = []
    
    print(f"--- Scanning {len(json_files)} JSON files for distance discrepancies > {DISCREPANCY_THRESHOLD_KM} km ---\n")
    
    # Process each JSON file as a primary file
    for json_file in sorted(json_files):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                main_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            continue  # Skip files that can't be read
        
        main_origin = main_data.get("origin")
        destinations = main_data.get("destinations", [])
        
        if not main_origin or not destinations:
            continue  # Skip files with missing data
        
        # Check each destination in this file
        for dest_entry in destinations:
            destination_name = dest_entry["name"]
            distance_forward = dest_entry["distance_km"]
            destination_filename = normalize_name_to_filename(destination_name)
            
            try:
                with open(destination_filename, 'r', encoding='utf-8') as f:
                    dest_data = json.load(f)
                
                distance_backward = None
                for reciprocal_entry in dest_data.get("destinations", []):
                    if reciprocal_entry["name"] == main_origin:
                        distance_backward = reciprocal_entry["distance_km"]
                        break
                
                if distance_backward is None:
                    continue  # Skip if reciprocal not found
                
                discrepancy = abs(distance_forward - distance_backward)
                
                # Only store if exceeds threshold
                if discrepancy > DISCREPANCY_THRESHOLD_KM:
                    # Create a unique key to avoid duplicates (sort names alphabetically)
                    pair_key = tuple(sorted([main_origin, destination_name]))
                    discrepancy_data = {
                        "pair_key": pair_key,
                        "origin": main_origin,
                        "destination": destination_name,
                        "forward_km": distance_forward,
                        "backward_km": distance_backward,
                        "discrepancy": discrepancy
                    }
                    large_discrepancies.append(discrepancy_data)
            
            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                continue  # Skip if destination file can't be processed
    
    # Remove duplicates (same pair reported from both directions)
    unique_discrepancies = {}
    for item in large_discrepancies:
        key = item["pair_key"]
        if key not in unique_discrepancies:
            unique_discrepancies[key] = item
    
    # Sort by discrepancy size (largest first)
    results = sorted(unique_discrepancies.values(), key=lambda x: x['discrepancy'], reverse=True)
    
    # --- OUTPUT ONLY LARGE DISCREPANCIES ---
    if results:
        print(f"--- Found {len(results)} discrepancies > {DISCREPANCY_THRESHOLD_KM} km ---\n")
        for item in results:
            print(f"Discrepancy: {item['discrepancy']:.2f} km")
            print(f"  {item['origin']} ↔ {item['destination']}")
            print(f"  Forward:  {item['forward_km']} km")
            print(f"  Backward: {item['backward_km']} km")
            print()
    else:
        print(f"✅ No discrepancies exceeding {DISCREPANCY_THRESHOLD_KM} km were found!")



if __name__ == "__main__":
    check_distances()
