#!/usr/bin/env python3
"""
Generate sv_phoneme_inventory.json from Synthesizer V installation files.

This script reads the *-phones.txt files from your local Synthesizer V installation
and generates a JSON file containing all phoneme inventories organized by notation
system and language.

Usage:
    python generate_phoneme_inventory.py [path_to_clf_data]

If no path is provided, defaults to:
    C:\Program Files\Synthesizer V Studio 2 Pro\clf-data
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict


def parse_phones_file(file_path):
    """Parse a *-phones.txt file and return a dict of phonemes by category."""
    phonemes = defaultdict(list)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                parts = line.split()
                if len(parts) >= 2:
                    phoneme = parts[0]
                    category = parts[1]
                    phonemes[category].append(phoneme)
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
        return None

    return dict(phonemes)


def generate_inventory(clf_data_path):
    """Generate phoneme inventory from Synthesizer V clf-data directory."""

    clf_data_path = Path(clf_data_path)

    if not clf_data_path.exists():
        print(f"Error: Directory not found: {clf_data_path}", file=sys.stderr)
        print("Please provide the path to your Synthesizer V clf-data directory.", file=sys.stderr)
        return None

    inventory = {}

    # Define the files to parse and their structure in the output
    language_files = {
        "arpabet": {
            "english": "english-arpabet-phones.txt"
        },
        "romaji": {
            "japanese": "japanese-romaji-phones.txt"
        },
        "xsampa": {
            "mandarin": "mandarin-xsampa-phones.txt",
            "cantonese": "cantonese-xsampa-phones.txt",
            "spanish": "spanish-xsampa-phones.txt",
            "korean": "korean-xsampa-phones.txt"
        }
    }

    # Parse each language file
    for notation, languages in language_files.items():
        if notation not in inventory:
            inventory[notation] = {}

        for language, filename in languages.items():
            file_path = clf_data_path / filename

            if not file_path.exists():
                print(f"Warning: File not found: {file_path}", file=sys.stderr)
                continue

            print(f"Processing {language} ({notation})...")
            phonemes = parse_phones_file(file_path)

            if phonemes:
                inventory[notation][language] = phonemes

    # Add common phonemes (silence, breath, etc.) that appear across languages
    # These are typically present in multiple files
    inventory["common"] = {
        "glottal_stop": ["cl"],
        "silence": ["sil"],
        "breath": ["br"]
    }

    return inventory


def main():
    # Default path for Windows installation
    default_path = r"C:\Program Files\Synthesizer V Studio 2 Pro\clf-data"

    # Use command-line argument if provided, otherwise use default
    if len(sys.argv) > 1:
        clf_data_path = sys.argv[1]
    else:
        clf_data_path = default_path

    print(f"Generating phoneme inventory from: {clf_data_path}")
    print()

    inventory = generate_inventory(clf_data_path)

    if inventory is None:
        sys.exit(1)

    # Determine output path (mappings directory relative to this script)
    script_dir = Path(__file__).parent
    output_dir = script_dir / "mappings"
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "sv_phoneme_inventory.json"

    # Write the JSON file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(inventory, f, indent=4, ensure_ascii=False)

        print()
        print(f"SUCCESS: Generated phoneme inventory at: {output_file}")
        print()
        print("The phoneme inventory has been created and can be used as a reference")
        print("when creating new language mappings.")
        print()
        print("Note: This file is gitignored and for local development use only.")

    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
