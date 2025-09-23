#!/usr/bin/env python3
import argparse
import json
import sys
import re
from phonemizer import phonemize
import itertools
import pyphen
import difflib


def load_mapping(map_file: str):
    """Load mapping file as JSON."""
    try:
        with open(map_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Could not read file '{map_file}': {e}", file=sys.stderr)
        sys.exit(1)


def project_syllables_from_ipa(syllable_ipa_list, word_ipa):
    """
    Align syllable-level IPA (possibly incorrect) with word-level IPA (correct),
    and project syllable boundaries onto the correct IPA.
    Handles geminate consonants at syllable boundaries.
    
    syllable_ipa_list: e.g. ['feːl', 'leː']
    word_ipa:          e.g. 'fɛlə'
    
    returns: list of IPA syllables with corrected phonology
             e.g. ['fɛl', 'lə']
    """
    # Flatten the syllable IPA
    flat_syl_ipa = "".join(syllable_ipa_list)
    
    # Align flat syllable IPA vs. word IPA
    sm = difflib.SequenceMatcher(None, flat_syl_ipa, word_ipa)
    ops = sm.get_opcodes()
    
    # Build alignment
    alignment = []
    for tag, i1, i2, j1, j2 in ops:
        if tag in ("equal", "replace"):
            for k in range(max(i2 - i1, j2 - j1)):
                c1 = flat_syl_ipa[i1 + k] if i1 + k < i2 else "_"
                c2 = word_ipa[j1 + k] if j1 + k < j2 else "_"
                alignment.append((c1, c2))
        elif tag == "insert":
            for k in range(j1, j2):
                alignment.append(("_", word_ipa[k]))
        elif tag == "delete":
            for k in range(i1, i2):
                alignment.append((flat_syl_ipa[k], "_"))
    
    # Where should syllable boundaries go?
    boundary_positions = []
    pos = 0
    for syl in syllable_ipa_list[:-1]:
        pos += len(syl)
        boundary_positions.append(pos)
    
    # Walk alignment, cutting at boundaries
    result = []
    buffer = []
    flat_index = 0
    for c1, c2 in alignment:
        if c2 != "_":
            buffer.append(c2)
        if c1 != "_":
            flat_index += 1
            if flat_index in boundary_positions:
                syll = "".join(buffer)
                result.append(syll)
                buffer = []
    
    if buffer:
        result.append("".join(buffer))
    
    # Geminate fix
    fixed_result = []
    for i, syl in enumerate(result):
        fixed_result.append(syl)
        if i < len(result) - 1:
            # Check the original syllable IPA input
            left = syllable_ipa_list[i]
            right = syllable_ipa_list[i+1]
            if left and right and left[-1] == right[0]:
                # If geminate in input, make sure next syllable starts with it
                if not result[i+1].startswith(left[-1]):
                    result[i+1] = left[-1] + result[i+1]
    return fixed_result


def ipa_convert(text: str, lang: str, phoneme_map = None, key_lengths = None) -> list[list[str]]:
    """Perform syllabification and convert input text into IPA using phonemizer (no punctuation, no stress).

    Returns:
        ipa_list (list[list[str]]): IPA translation of the input text.
                                    Each element in the outer list is a word
                                    and each str in a word is a syllable.
    """
    # syllabify words
    dic = pyphen.Pyphen(lang=lang)
    words = text.strip().split()
    syllabified_words = [dic.inserted(word) for word in words]

    # post-processing
    vowels = "aeiouyäöü"
    for idx, word in enumerate(syllabified_words):
        syls = word.split("-")
        # add unrecognized syllables
        if len(syls) == 1:
            if syls[0][:4].lower() == "über":
                syls = [syls[0][0], "ber" + syls[0][4:]]
            elif syls[0][:3].lower() == "ehe":
                syls = [syls[0][0], "he" + syls[0][3:]]
            elif re.search(r'[aeiouyäöü][eE]$', syls[0][-2:]):
                syls = [syls[0][:-1], syls[0][-1]]
            syllabified_words[idx] = [s for s in syls]
            continue
        # move grapheme left
        else:
            for i in range(len(syls)-1):
                if syls[i+1].startswith("phth"):
                    syls[i] += "ph"
                    syls[i+1] = syls[i+1][2:]
        i = 0
        # fix falsely split syllables if they only contain consonants
        while i < len(syls):
            if not any([v in syls[i].lower() for v in vowels]):
                if i == 0:
                    syls[0] = syls[0] + syls[1]
                    syls.pop(1)
                elif i > 0:
                    syls[i - 1] = syls[i - 1] + syls[i]
                    syls.pop(i)
            else:
                i += 1
        # replace entry with corrected word
        syllabified_words[idx] = [s for s in syls]

    # translate syllables to IPA
    syllable_tokens = [syl for word in syllabified_words for syl in word]
    ipa_list = [re.sub(r"[ː‿‖ ]", "", syl) for syl in phonemize(
        syllable_tokens,
        language="fr-fr" if lang == "fr" else lang,
        backend="espeak",
        strip=True,
        preserve_punctuation=False,
        with_stress=False,
        language_switch="remove-flags"
    )]
    print(ipa_list)

    # find words with more than 1 syllable
    word_tokens = ["".join(w) for w in syllabified_words if len(w) > 1]
    # translate those words
    ipa_list_words = [re.sub(r"[ː‿‖ ]", "", word) for word in phonemize(
        word_tokens,
        language="fr-fr" if lang == "fr" else lang,
        backend="espeak",
        strip=True,
        preserve_punctuation=False,
        with_stress=False,
        language_switch="remove-flags"
    )]
    print(ipa_list_words)

    ipa_list_syllables = []
    j = k = 0
    for i, word in enumerate(syllabified_words):
        len_w = len(word)
        if len_w == 1:
            ipa_list_syllables.append([ipa_list[j]])
        else:
            syllable_ipa_list = ipa_list[j:j+len_w]
            word_ipa = ipa_list_words[k]
            #print(syllable_ipa_list, word_ipa)
            ipa_list_syllables.append(project_syllables_from_ipa(syllable_ipa_list, word_ipa))
            k += 1
        j += len_w
    print(ipa_list_syllables)
    return ipa_list_syllables


def ipa_list_to_str(ipa_list):
    ipa_words = []
    for word in ipa_list:
        ipa_words.append("-".join(word))
    return " ".join(ipa_words)


def get_syllable_alternatives(phoneme_seq: list[str], phoneme_map: dict, n_alternatives: int = 0, phoneme_edit: bool = False) -> list[dict]:
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

    # Step 1: restrict mapping to only relevant phonemes
    phoneme_seq_map = {ph: phoneme_map[ph] for ph in phoneme_seq if ph in phoneme_map}

    # Step 2: find maximum option length
    max_weight_all = max(len(options) for options in phoneme_seq_map.values())

    alternatives = []

    # Step 3: cartesian product over all options for each phoneme in sequence
    option_lists = [phoneme_seq_map[ph] for ph in phoneme_seq]

    for combo in itertools.product(*option_lists):
        mapping = []
        total_weight = 0.0
        langs = []

        for ph, chosen_entry in zip(phoneme_seq, combo):
            idx = phoneme_seq_map[ph].index(chosen_entry)
            phoneme_weight = (max_weight_all - idx) + chosen_entry.get("weight", 0.0)

            total_weight += phoneme_weight
            langs.append(chosen_entry["lang"])

            # preserve "weight" only if present in the original
            entry_copy = {k: v for k, v in chosen_entry.items()}
            mapping.append(entry_copy)

        # count unique languages
        n_langs = len(set(langs))

        alternatives.append(
            {
                "weight": total_weight,
                "n_langs": n_langs,
                "mapping": mapping,
            }
        )
    # sort alternatives
    alternatives.sort(key=lambda x: (-x["weight"], x["n_langs"]))
    # filter and return results
    min_n_langs = min(entry["n_langs"] for entry in alternatives)
    if min_n_langs > 1 and not phoneme_edit:
        print(f"Warning: The IPA sequence '{''.join(phoneme_seq)}' cannot be mapped into a single language.", file=sys.stderr)
    results = alternatives if phoneme_edit else [entry for entry in alternatives if entry["n_langs"] == min_n_langs]
    if n_alternatives == -1:
        return results
    elif n_alternatives >= 0:
        return results[:min(len(results), n_alternatives + 1)]


def segment_syllable(syllable: str, phoneme_map, key_lengths):
    """Split a syllable into the longest possible phoneme units from the mapping."""
    segments = []
    i = 0
    while i < len(syllable):
        match = None
        for L in key_lengths:  # try longest keys first
            chunk = syllable[i : i + L]
            if chunk in phoneme_map:
                match = chunk
                break
        if match:
            segments.append(match)
            i += len(match)
        else:
            segments.append(syllable[i])
            i += 1
    return segments


def convert_ipa_to_sv(ipa_list, phoneme_map, key_lengths, n_alternatives: int = 0, phoneme_edit: bool = False):
    result = []
    for word in ipa_list:
        sv_word = []
        for syl in word:
            phoneme_seq = segment_syllable(syl, phoneme_map, key_lengths)
            sv_word.append(get_syllable_alternatives(phoneme_seq, phoneme_map, n_alternatives, phoneme_edit))
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

    for group in alternatives:  # top-level groups
        group_strings = []
        for alt_list in group:  # each sub-group
            alt_strings = []
            for entry in alt_list:  # each alternative (dict with weight, n_langs, mapping)
                tokens = []
                last_lang = None
                for ph_entry in entry["mapping"]:
                    lang = ph_entry["lang"]
                    ph = ph_entry["ph"]
                    if lang != last_lang:
                        tokens.append(f"<{lang}>")
                        last_lang = lang
                    tokens.append(ph)
                alt_strings.append(" ".join(tokens))
            group_strings.append(" | ".join(alt_strings))
        # Wrap each sub-group in brackets
        output_groups.append(" - ".join(f"[{s}]" if " | " in s else f"{s}" for s in group_strings))

    return "\n".join(output_groups)


def main():
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
        default="mappings\de.json",
        help="Path to the JSON mapping file (default: mappings\de.json)",
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

    # Load mapping
    phoneme_map = load_mapping(args.map_file)
    key_lengths = sorted(set(len(k) for k in phoneme_map.keys()), reverse=True)

    # Load input text
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            text = f.read()
    elif args.words:
        text = " ".join(args.words)
    else:
        text = sys.stdin.read()

    ipa_list = ipa_convert(text, args.lang, phoneme_map, key_lengths)
    print(ipa_list_to_str(ipa_list))
    alternatives = convert_ipa_to_sv(ipa_list, phoneme_map, key_lengths, args.alternatives, args.phoneme_edit)
    output_string = get_output_string(alternatives)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_string)
    else:
        print(output_string)


if __name__ == "__main__":
    main()
