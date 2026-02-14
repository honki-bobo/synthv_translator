#!/usr/bin/env python3
"""
Synthesizer V Translator - Text to SynthV Phoneme Converter

This script translates text from various languages into phoneme sequences that are
compatible with Synthesizer V by Dreamtonics. It enables singing in languages that
aren't natively supported by SynthV voices.

Translation Pipeline:
1. Text Input → Syllabification (pyphen)
2. Syllables → IPA phonemes (eSpeak NG via phonemizer)
3. IPA alignment and correction
4. IPA → SynthV phoneme mapping
5. Output formatted phoneme sequences with language tags

The script uses mapping files (JSON) that define how IPA phonemes convert to
SynthV phonemes across different voice languages (English, Spanish, Japanese, etc.).

Author: Martin Blankenburg
License: MIT
Repository: https://github.com/honki-bobo/synthv_translator
"""

import argparse
import difflib
import itertools
import json
import re
import sys

import pyphen
from phonemizer import phonemize


def load_mapping(map_file: str) -> dict:
    """
    Load and parse a phoneme mapping file.

    The mapping file defines how IPA phonemes from the source language are
    converted to Synthesizer V phonemes. It contains:
    - vowels_orth: Orthographic vowels for syllabification
    - ipa_process: Regex rules for IPA post-processing
    - phoneme_map: IPA → SynthV phoneme mappings

    Args:
        map_file: Path to the JSON mapping file

    Returns:
        dict: Parsed mapping configuration

    Exits:
        With error code 1 if the file cannot be read or parsed
    """
    try:
        with open(map_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Could not read file '{map_file}': {e}", file=sys.stderr)
        sys.exit(1)


def project_syllables_from_ipa(
    syllable_ipa_list: list[str], word_ipa: str
) -> list[str]:
    """
    Align syllable-level IPA with word-level IPA and project syllable boundaries.

    When eSpeak NG phonemizes individual syllables vs. whole words, the results
    can differ due to phonological processes (assimilation, vowel reduction, etc.).
    This function aligns the syllable-level IPA (which has known boundaries but
    possibly incorrect phonology) with the word-level IPA (which has correct
    phonology but no boundaries), then projects the syllable boundaries onto
    the correct phonology.

    The function also handles geminate consonants (doubled consonants at syllable
    boundaries like "tt" in "Butter").

    Args:
        syllable_ipa_list: List of IPA strings, one per syllable
                          Example: ['feːl', 'leː']
        word_ipa: IPA string for the whole word (correct phonology)
                 Example: 'fɛlə'

    Returns:
        list[str]: List of IPA syllables with corrected phonology
                   Example: ['fɛl', 'lə']

    Algorithm:
        1. Flatten syllable IPA into single string
        2. Use sequence alignment (difflib) to match syllable IPA to word IPA
        3. Walk through alignment and cut at original syllable boundaries
        4. Fix geminate consonants that span syllable boundaries
    """
    # Flatten the syllable IPA into a single string for alignment
    flat_syl_ipa = "".join(syllable_ipa_list)

    # Align flat syllable IPA vs. word IPA using sequence matching
    # This finds the optimal character-by-character alignment
    sm = difflib.SequenceMatcher(None, flat_syl_ipa, word_ipa)
    ops = sm.get_opcodes()

    # Build character-level alignment as list of (syllable_char, word_char) tuples
    # Use "_" to represent gaps in the alignment
    alignment = []
    for tag, i1, i2, j1, j2 in ops:
        if tag in ("equal", "replace"):
            # Characters match or are substituted
            for k in range(max(i2 - i1, j2 - j1)):
                c1 = flat_syl_ipa[i1 + k] if i1 + k < i2 else "_"
                c2 = word_ipa[j1 + k] if j1 + k < j2 else "_"
                alignment.append((c1, c2))
        elif tag == "insert":
            # Character(s) present in word IPA but not in syllable IPA
            for k in range(j1, j2):
                alignment.append(("_", word_ipa[k]))
        elif tag == "delete":
            # Character(s) present in syllable IPA but not in word IPA
            for k in range(i1, i2):
                alignment.append((flat_syl_ipa[k], "_"))

    # Calculate where syllable boundaries should be in the flattened syllable IPA
    # These positions will be used to cut the aligned word IPA
    boundary_positions = []
    pos = 0
    for syl in syllable_ipa_list[:-1]:  # Exclude last syllable (no boundary after it)
        pos += len(syl)
        boundary_positions.append(pos)

    # Walk through alignment and cut at the calculated boundary positions
    # Build up corrected syllables using the word IPA characters
    result = []
    buffer = []  # Accumulates characters for current syllable
    flat_index = 0  # Position in the flattened syllable IPA

    for c1, c2 in alignment:
        # Add word IPA character to buffer (if not a gap)
        if c2 != "_":
            buffer.append(c2)

        # Track position in syllable IPA
        if c1 != "_":
            flat_index += 1
            # Check if we've reached a syllable boundary
            if flat_index in boundary_positions:
                syll = "".join(buffer)
                result.append(syll)
                buffer = []  # Start new syllable

    # Add the final syllable
    if buffer:
        result.append("".join(buffer))

    # Fix geminate consonants at syllable boundaries
    # If the original syllables had a doubled consonant (e.g., "tt"),
    # ensure the corrected syllables maintain this
    fixed_result = []
    for i, syl in enumerate(result):
        fixed_result.append(syl)
        if i < len(result) - 1:
            # Check if there's a geminate in the original syllabification
            left = syllable_ipa_list[i]
            right = syllable_ipa_list[i + 1]
            if left and right and left[-1] == right[0]:
                # Geminate found: last char of left = first char of right
                # Make sure next syllable starts with the geminate consonant
                if not result[i + 1].startswith(left[-1]):
                    result[i + 1] = left[-1] + result[i + 1]

    return fixed_result


def syllabify_orthographically(
    text: str, lang: str = "de", vowels_orth: str = "aeiouyäöüÿ"
) -> list[list[str]]:
    """
    Split text into syllables based on orthographic rules.

    Uses pyphen (based on TeX hyphenation patterns) for initial syllabification,
    then applies language-specific post-processing rules to fix common issues:
    - Unsyllabified words (e.g., loanwords)
    - Consonant-only "syllables" from incorrect splits
    - Special grapheme combinations (e.g., "phth")

    Args:
        text: Input text to syllabify
        lang: Language code for pyphen (e.g., "de", "fr", "it")
        vowels_orth: String containing all orthographic vowels for the language

    Returns:
        list[list[str]]: List of words, each word is a list of syllable strings
                        Example: [["Hal", "lo"], ["Welt"]]
    """
    # Use pyphen to syllabify each word
    dic = pyphen.Pyphen(lang=lang)
    words = text.strip().split()
    syllabified_words = [dic.inserted(word) for word in words]

    # Post-processing to fix pyphen's limitations
    # Regex patterns for special cases
    vowel_e_re = re.compile(rf"[{re.escape(vowels_orth)}][eE]$")  # Vowel + e at end
    vowel_hb_re = re.compile(rf"[{re.escape(vowels_orth)}][hb]$")  # Vowel + h/b at end

    for idx, word in enumerate(syllabified_words):
        syls = word.split("-")

        # Handle unsyllabified words (pyphen returned no hyphens)
        if len(syls) == 1:
            # Try to split at vowel+h or vowel+b patterns (e.g., "ah" → "a-h")
            if vowel_hb_re.search(syls[0][:2].lower()):
                syls = [syls[0][0], syls[0][1:]]
            # Try to split before final 'e' if preceded by vowel (e.g., "ae" → "a-e")
            elif vowel_e_re.search(syls[0][-2:].lower()):
                syls = [syls[0][:-1], syls[0][-1]]

            syllabified_words[idx] = [s for s in syls]
            continue

        # Fix grapheme clusters that should stay together
        # Move "ph" from right syllable to left when followed by "th"
        for i in range(len(syls) - 1):
            if syls[i + 1].startswith("phth"):
                syls[i] += "ph"
                syls[i + 1] = syls[i + 1][2:]

        # Merge consonant-only syllables with adjacent syllables
        # A syllable with no vowels is likely an incorrect split
        i = 0
        while i < len(syls):
            if not any([v in syls[i].lower() for v in vowels_orth]):
                # This syllable has no vowels - merge it
                if i == 0:
                    # First syllable: merge with next
                    syls[0] = syls[0] + syls[1]
                    syls.pop(1)
                else:
                    # Other syllable: merge with previous
                    syls[i - 1] = syls[i - 1] + syls[i]
                    syls.pop(i)
            else:
                i += 1

        # Update word with corrected syllables
        syllabified_words[idx] = [s for s in syls]

    return syllabified_words


def post_process_ipa(ipa_string: str, ipa_process: list[list] = []) -> str:
    """
    Post-process IPA output from eSpeak NG.

    Removes IPA symbols that aren't needed for phoneme mapping (length marks,
    linking symbols, etc.) and applies language-specific regex transformations
    defined in the mapping file.

    Args:
        ipa_string: IPA string from eSpeak
        ipa_process: List of [pattern, replacement] regex pairs from mapping file
                    Example: [["([^vowels])(r)", "\\1ʁ"]]

    Returns:
        str: Processed IPA string ready for phoneme mapping

    Removed symbols:
        ː (length mark)
        ‿ (linking mark)
        ‖ (boundary mark)
        (space)
    """
    # Remove IPA diacritics and symbols not used in phoneme mapping
    ipa_string = re.sub(r"[ː‿‖ ]", "", ipa_string)

    # Apply language-specific IPA transformations from mapping file
    for rule in ipa_process:
        ipa_string = re.sub(rule[0], rule[1], ipa_string)

    return ipa_string


def ipa_convert(
    text: str, lang: str = "de", vowels_orth: str = "aeiouyäöüÿ", ipa_process: list = []
) -> list[list[str]]:
    """
    Convert text to IPA phonemes with syllable boundaries.

    This is the core function that coordinates the text → IPA conversion pipeline.
    It uses a dual-pass strategy:
    1. Phonemize individual syllables (preserves boundaries but may have wrong phonology)
    2. Phonemize whole words (correct phonology but no boundaries)
    3. Align the two to get syllables with correct phonology

    This approach handles phonological processes that occur across syllable
    boundaries (e.g., assimilation, vowel reduction).

    Args:
        text: Input text to convert
        lang: Language code for eSpeak (de, fr, it, pt, ru, etc.)
        vowels_orth: Orthographic vowels for syllabification
        ipa_process: Regex rules for IPA post-processing

    Returns:
        list[list[str]]: Nested list structure:
                        - Outer list: words
                        - Inner list: syllables (as IPA strings)
                        Example: [['ha', 'lo'], ['vɛlt']]

    Note:
        French requires "fr-fr" as eSpeak language code
    """
    # Step 1: Syllabify text orthographically
    syllabified_words = syllabify_orthographically(text, lang, vowels_orth)

    # Step 2: Phonemize each syllable individually
    # Flatten all syllables into a single list for batch processing
    syllable_tokens = [syl for word in syllabified_words for syl in word]
    ipa_list = [
        post_process_ipa(syl, ipa_process)
        for syl in phonemize(
            syllable_tokens,
            language="fr-fr" if lang == "fr" else lang,  # eSpeak uses "fr-fr" not "fr"
            backend="espeak",
            strip=True,
            preserve_punctuation=False,
            with_stress=False,  # Disable stress marks
            language_switch="remove-flags",  # Don't insert language switch markers
        )
    ]

    # Step 3: Phonemize multi-syllable words as whole units
    # This gives us the correct phonology for the whole word
    word_tokens = ["".join(w) for w in syllabified_words if len(w) > 1]
    ipa_list_words = [
        post_process_ipa(word, ipa_process)
        for word in phonemize(
            word_tokens,
            language="fr-fr" if lang == "fr" else lang,
            backend="espeak",
            strip=True,
            preserve_punctuation=False,
            with_stress=False,
            language_switch="remove-flags",
        )
    ]

    # Step 4: Combine syllable boundaries with correct word phonology
    # For single-syllable words: use syllable IPA directly
    # For multi-syllable words: align syllable IPA with word IPA
    ipa_list_syllables = []
    j = 0  # Index into syllable IPA list
    k = 0  # Index into word IPA list

    for _, word in enumerate(syllabified_words):
        len_w = len(word)

        if len_w == 1:
            # Single syllable: use as-is
            ipa_list_syllables.append([ipa_list[j]])
        else:
            # Multi-syllable: align syllable boundaries with word phonology
            syllable_ipa_list = ipa_list[j : j + len_w]
            word_ipa = ipa_list_words[k]
            ipa_list_syllables.append(
                project_syllables_from_ipa(syllable_ipa_list, word_ipa)
            )
            k += 1

        j += len_w

    # Optional debug output: print IPA syllables (if terminal supports Unicode)
    # try:
    #     print(ipa_list_syllables)
    # except UnicodeEncodeError:
    #     # Terminal doesn't support Unicode - skip debug output
    #     pass

    return ipa_list_syllables


def ipa_list_to_str(ipa_list: list[list[str]]) -> str:
    """
    Convert IPA syllable list to human-readable string.

    Joins syllables with hyphens and words with spaces.

    Args:
        ipa_list: Nested list of IPA syllables per word

    Returns:
        str: Formatted IPA string
             Example: "ha-lo vɛlt" for [['ha', 'lo'], ['vɛlt']]
    """
    ipa_words = []
    for word in ipa_list:
        ipa_words.append("-".join(word))
    return " ".join(ipa_words)


def get_syllable_alternatives(
    phoneme_seq: list[str],
    phoneme_map: dict,
    n_alternatives: int = 0,
    phoneme_edit: bool = False,
) -> list[dict]:
    """
    Generate all possible language-specific phoneme combinations with weights and single_lang flag.

    Parameters:
        phoneme_seq (List[str]): Sequence of IPA phonemes (e.g., ["l", "j", "r"])
        phoneme_map (Dict[str, List[Dict[str, Any]]]): Mapping from IPA phonemes
            to a list of dicts with {"lang": ..., "ph": ..., "weight": ...}
        n_alternatives (int): Number of alternatives to return. -1 = all, default: 0
        phoneme_edit (bool): Turn language switching within the phoneme_seq on/off. Default: False (off)

    Returns:
        List[Dict[str, Any]]: Each dict has keys {"weight", "single_lang", "mapping"}.
    """

    # Step 1: Filter phoneme map to only include phonemes in this sequence
    # Ignore phonemes that aren't in the mapping (shouldn't happen normally)
    phoneme_seq_map = {ph: phoneme_map[ph] for ph in phoneme_seq if ph in phoneme_map}

    # Step 2: Calculate maximum number of alternatives for any phoneme
    # This is used for position-based weighting
    max_weight_all = max(len(options) for options in phoneme_seq_map.values())

    alternatives = []

    # Step 3: Generate all possible combinations using cartesian product
    # For each phoneme, we have multiple language options
    # Product generates every possible combination across all phonemes
    option_lists = [phoneme_seq_map[ph] for ph in phoneme_seq]

    for combo in itertools.product(*option_lists):
        # Each combo is one specific choice for each phoneme
        mapping = []
        total_weight = 0.0
        langs = []

        for ph, chosen_entry in zip(phoneme_seq, combo):
            # Calculate weight for this phoneme choice
            idx = phoneme_seq_map[ph].index(chosen_entry)
            # Weight = position bonus + custom weight
            # Earlier positions get higher bonus
            phoneme_weight = (max_weight_all - idx) + chosen_entry.get("weight", 0.0)

            total_weight += phoneme_weight
            langs.append(chosen_entry["lang"])

            # Copy the entry to preserve all fields
            entry_copy = {k: v for k, v in chosen_entry.items()}
            mapping.append(entry_copy)

        # Count how many different languages this combination uses
        n_langs = len(set(langs))

        alternatives.append(
            {
                "weight": total_weight,
                "n_langs": n_langs,
                "mapping": mapping,
            }
        )

    # Sort alternatives by weight (descending) and number of languages (ascending)
    # Prefer high weight and fewer language switches
    alternatives.sort(key=lambda x: (-x["weight"], x["n_langs"]))

    # Filter results based on phoneme_edit flag
    min_n_langs = min(entry["n_langs"] for entry in alternatives)
    if min_n_langs > 1 and not phoneme_edit:
        # Warn if no single-language mapping exists and phoneme_edit is disabled
        print(
            f"Warning: The IPA sequence '{''.join(phoneme_seq)}' cannot be mapped into a single language.",
            file=sys.stderr,
        )

    # If phoneme_edit is True, allow language switching within syllable
    # Otherwise, only return options with minimum number of languages
    results = (
        alternatives
        if phoneme_edit
        else [entry for entry in alternatives if entry["n_langs"] == min_n_langs]
    )

    # Return requested number of alternatives
    if n_alternatives == -1:
        return results  # Return all
    elif n_alternatives >= 0:
        return results[: min(len(results), n_alternatives + 1)]  # Return top N+1


def segment_syllable(
    syllable: str, phoneme_map: dict, key_lengths: list[int]
) -> list[str]:
    """
    Segment an IPA syllable into individual phonemes using longest-match-first.

    IPA strings can contain multi-character phonemes (e.g., "tʃ" for ch, "aɪ" for ay).
    This function greedily matches the longest possible phoneme at each position.

    Args:
        syllable: IPA string to segment (e.g., "tʃaɪ")
        phoneme_map: Dict mapping IPA phonemes to SynthV options
        key_lengths: List of phoneme lengths in phoneme_map, sorted descending
                    (e.g., [3, 2, 1] to try 3-char, then 2-char, then 1-char)

    Returns:
        list[str]: List of IPA phoneme strings
                  Example: "tʃaɪ" → ["tʃ", "aɪ"]

    Algorithm:
        Greedy longest-match-first:
        - At each position, try matching phonemes from longest to shortest
        - Once a match is found, advance by the matched length
        - If no match, take single character and advance by 1
    """
    segments = []
    i = 0

    while i < len(syllable):
        match = None

        # Try to match phonemes from longest to shortest
        for L in key_lengths:
            chunk = syllable[i : i + L]
            if chunk in phoneme_map:
                match = chunk
                break  # Found a match, use it

        if match:
            # Matched a known phoneme
            segments.append(match)
            i += len(match)
        else:
            # No match found - take single character
            # This handles unmapped phonemes or edge cases
            segments.append(syllable[i])
            i += 1

    return segments


def convert_ipa_to_sv(
    ipa_list: list[list[str]],
    phoneme_map: dict,
    key_lengths: list[int],
    n_alternatives: int = 0,
    phoneme_edit: bool = False,
) -> list[list[list[dict]]]:
    """
    Convert IPA syllables to Synthesizer V phoneme sequences.

    For each syllable:
    1. Segment the IPA string into individual phonemes
    2. Generate alternative SynthV phoneme mappings

    Args:
        ipa_list: Nested list of IPA syllables [word][syllable]
        phoneme_map: IPA → SynthV phoneme mapping dictionary
        key_lengths: Sorted list of phoneme lengths for segmentation
        n_alternatives: Number of alternatives to return (0=best only, -1=all)
        phoneme_edit: Allow language switching within syllables

    Returns:
        Nested list structure: [word][syllable][alternative]
        Each alternative is a dict with:
            - "weight": float (higher is better)
            - "n_langs": int (number of languages used)
            - "mapping": list of {"lang": str, "ph": str, ...} dicts
    """
    result = []

    for word in ipa_list:
        sv_word = []

        for syl in word:
            # Segment IPA syllable into individual phonemes
            phoneme_seq = segment_syllable(syl, phoneme_map, key_lengths)

            # Generate alternative SynthV mappings for this phoneme sequence
            alternatives = get_syllable_alternatives(
                phoneme_seq, phoneme_map, n_alternatives, phoneme_edit
            )
            sv_word.append(alternatives)

        result.append(sv_word)

    return result


def get_output_string(alternatives) -> str:
    """
    Convert nested list of phoneme mapping alternatives into a formatted string.

    Parameters:
        alternatives: Nested list where each innermost list contains alternative mappings,
                      each mapping is a dict with {"lang", "ph", ...}

    Returns:
        str: Formatted string like
             "[<spanish> f r <english> ih <japanese> ts | <spanish> f r i <japanese> ts] ..."
    """

    output_groups = []

    # Process each word
    for group in alternatives:
        group_strings = []

        # Process each syllable in the word
        for alt_list in group:
            alt_strings = []

            # Process each alternative for this syllable
            for entry in alt_list:
                tokens = []
                last_lang = None

                # Build phoneme sequence with language tags
                for ph_entry in entry["mapping"]:
                    lang = ph_entry["lang"]
                    ph = ph_entry["ph"]

                    # Insert language tag when language changes
                    if lang != last_lang:
                        tokens.append(f"<{lang}>")
                        last_lang = lang

                    tokens.append(ph)

                alt_strings.append(" ".join(tokens))

            # Join alternatives with " | " separator
            group_strings.append(" | ".join(alt_strings))

        # Wrap multi-alternative syllables in brackets
        formatted = [f"[{s}]" if " | " in s else f"{s}" for s in group_strings]

        # Remove redundant language tags between consecutive syllables
        # e.g., "<spanish> g u - <spanish> t e" → "<spanish> g u - t e"
        # Only when both syllables have no alternatives (no brackets)
        last_lang = None
        for i, s in enumerate(formatted):
            if s.startswith("["):
                # Bracketed syllable: language is ambiguous, reset tracking
                last_lang = None
            else:
                # Extract the leading language tag if present
                match = re.match(r"^<(\w+)>", s)
                if match:
                    current_lang = match.group(1)
                    if current_lang == last_lang:
                        # Same language as previous syllable: remove the redundant tag
                        formatted[i] = re.sub(r"^<\w+>\s*", "", s)

                # Track the last language tag used in this syllable
                # (could change mid-syllable due to language switching)
                all_langs = re.findall(r"<(\w+)>", s)
                last_lang = all_langs[-1] if all_langs else last_lang

        # Join syllables with " - " separator
        output_groups.append(" - ".join(formatted))

    # Join words with newlines
    return "\n".join(output_groups)


def main():
    """
    Main entry point for the command-line interface.

    Parses arguments, loads mapping file, converts text to IPA,
    maps IPA to SynthV phonemes, and outputs the result.
    """
    # Set up command-line argument parser
    parser = argparse.ArgumentParser(
        description="Text → Synthesizer V phoneme translator"
    )
    parser.add_argument(
        "-i", "--input", type=str, help="Input text file (optional, defaults to stdin)"
    )
    parser.add_argument(
        "-l",
        "--lang",
        type=str,
        choices=["de", "fr", "it", "pt", "ru"],
        default="de",
        help="Language for phonemization (default: de)",
    )
    parser.add_argument(
        "-m",
        "--map-file",
        type=str,
        default=None,
        help="Path to the JSON mapping file (default: auto-detected from language)",
    )
    parser.add_argument(
        "-a",
        "--alternatives",
        type=int,
        default=0,
        help="Show N alternatives. -1 = all (default: 0)",
    )
    parser.add_argument(
        "-p",
        "--phoneme-edit",
        action="store_true",
        help="Allow language switching per phoneme instead of per syllable",
    )
    parser.add_argument(
        "-o", "--output", type=str, help="Output file (optional, defaults to stdout)"
    )
    parser.add_argument(
        "words", nargs="*", help="Words to translate (ignored if -i is used)"
    )
    args = parser.parse_args()

    # Auto-detect mapping file based on language if not specified
    if args.map_file is None:
        args.map_file = f"mappings\\{args.lang}.json"

    # Load the phoneme mapping configuration
    mapping = load_mapping(args.map_file)
    phoneme_map = mapping["phoneme_map"]  # IPA → SynthV mappings
    vowels_orth = mapping["vowels_orth"]  # Orthographic vowels
    ipa_process = mapping["ipa_process"]  # IPA post-processing rules

    # Pre-calculate phoneme lengths for efficient segmentation
    # Sort descending so we try longest matches first
    key_lengths = sorted(set(len(k) for k in phoneme_map.keys()), reverse=True)

    # Load input text from file, command-line args, or stdin
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            text = f.read()
    elif args.words:
        text = " ".join(args.words)
    else:
        text = sys.stdin.read()

    # Translation pipeline:
    # 1. Text → IPA with syllable boundaries
    ipa_list = ipa_convert(text, args.lang, vowels_orth, ipa_process)

    # Optional: Print IPA representation for debugging
    # print(ipa_list_to_str(ipa_list))

    # 2. IPA → SynthV phonemes with alternatives
    alternatives = convert_ipa_to_sv(
        ipa_list, phoneme_map, key_lengths, args.alternatives, args.phoneme_edit
    )

    # 3. Format output with language tags
    output_string = get_output_string(alternatives)

    # Write output to file or stdout
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_string)
    else:
        print(output_string)


if __name__ == "__main__":
    main()
