import json
import os
import unicodedata

PRIMARY_FILE_TO_CHECK = "Riscani.json"
DISCREPANCY_THRESHOLD_KM = 19.0


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
    Main function to load the primary file and check distance consistency.
    It now reports all mismatches and errors, and a specific list of large discrepancies.
    """
    checked_count = 0
    mismatches = []
    errors = []
    # New list to store destinations with discrepancies greater than the threshold
    large_discrepancy_destinations = []

    # 1. Load the main file to be checked
    try:
        with open(PRIMARY_FILE_TO_CHECK, 'r', encoding='utf-8') as f:
            main_data = json.load(f)
    except FileNotFoundError:
        print(f"FATAL ERROR: The primary file '{PRIMARY_FILE_TO_CHECK}' was not found.")
        print("Please make sure the file exists and the variable is set correctly.")
        return
    except json.JSONDecodeError:
        print(f"FATAL ERROR: Could not parse the JSON in '{PRIMARY_FILE_TO_CHECK}'.")
        return

    main_origin = main_data.get("origin")
    destinations = main_data.get("destinations", [])

    if not main_origin or not destinations:
        print(f"FATAL ERROR: The file '{PRIMARY_FILE_TO_CHECK}' is missing 'origin' or 'destinations' key.")
        return

    print(f"--- Starting consistency check for distances from '{main_origin}' ---")

    # 2. Loop through each destination in the primary file
    for dest_entry in destinations:
        destination_name = dest_entry["name"]
        distance_forward = dest_entry["distance_km"]
        destination_filename = normalize_name_to_filename(destination_name)

        try:
            with open(destination_filename, 'r', encoding='utf-8') as f:
                dest_data = json.load(f)

            distance_backward = None
            reciprocal_found = False
            for reciprocal_entry in dest_data.get("destinations", []):
                if reciprocal_entry["name"] == main_origin:
                    distance_backward = reciprocal_entry["distance_km"]
                    reciprocal_found = True
                    break

            if not reciprocal_found:
                errors.append(f"[Missing Return] Could not find return distance for '{main_origin}' in file '{destination_filename}'")
                continue

            discrepancy = abs(distance_forward - distance_backward)
            if discrepancy > 0.01:
                # Store all mismatches
                mismatch_data = {
                    "origin": main_origin,
                    "destination": destination_name,
                    "forward_km": distance_forward,
                    "backward_km": distance_backward,
                    "discrepancy": discrepancy
                }
                mismatches.append(mismatch_data)

                # Check against the new threshold
                if discrepancy > DISCREPANCY_THRESHOLD_KM:
                    large_discrepancy_destinations.append(destination_name)
            else:
                checked_count += 1

        except FileNotFoundError:
            errors.append(f"[File Not Found] File '{destination_filename}' for destination '{destination_name}' was not found.")
        except (json.JSONDecodeError, KeyError) as e:
            errors.append(f"[File Error] Could not read or parse '{destination_filename}'. Error: {e}")

    # --- REPORTING ---
    print("\n--- Check Complete ---")

    # 3. Report all mismatches, sorted from largest to smallest discrepancy (as before)
    if mismatches:
        print(f"\n--- ❌ Found {len(mismatches)} Mismatches (sorted by discrepancy) ---")
        # Sort the list of mismatches by the 'discrepancy' value in descending order
        mismatches.sort(key=lambda x: x['discrepancy'], reverse=True)
        for item in mismatches:
            print(f"  [MISMATCH] Discrepancy: {item['discrepancy']:.2f} km")
            print(f"    - {item['origin']} -> {item['destination']}: {item['forward_km']} km")
            print(f"    - {item['destination']} -> {item['origin']}: {item['backward_km']} km")

    # 4. Report any errors found during the process
    if errors:
        print(f"\n--- ⚠️ Found {len(errors)} Errors ---")
        for error_msg in errors:
            print(f"  {error_msg}")

    # 5. Print the list of places with large discrepancies (NEW SECTION)
    if large_discrepancy_destinations:
        print(f"\n--- 🚨 Large Discrepancies (> {DISCREPANCY_THRESHOLD_KM:.1f} km) ---")
        # Sort the list alphabetically for clean presentation
        large_discrepancy_destinations.sort()
        # Format the list as required: x ; y ; z ; etc.
        list_output = " ; ".join(large_discrepancy_destinations)
        print(list_output)
    elif mismatches:
        print(f"\n--- 🚨 Large Discrepancies (> {DISCREPANCY_THRESHOLD_KM:.1f} km) ---")
        print("None of the mismatches exceeded the specified threshold.")

    # 6. Print the final summary
    print("\n--- Summary ---")
    print(f"✅ Consistent distances: {checked_count}")
    print(f"❌ Mismatches found:     {len(mismatches)}")
    print(f"⚠️ Errors encountered:   {len(errors)}")


if __name__ == "__main__":
    check_distances()
