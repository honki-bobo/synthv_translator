#!/usr/bin/env python3
import argparse
import json
import sys
import re
from phonemizer import phonemize
import pyphen
import itertools


def load_mapping(map_file: str):
    """Load mapping file as JSON."""
    try:
        with open(map_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Could not read file '{map_file}': {e}", file=sys.stderr)
        sys.exit(1)


def ipa_convert(text: str, lang: str) -> list[list[str]]:
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
            elif syls[0][:4].lower() == "neue":
                syls = [syls[0][0] + "eu", "e" + syls[0][4:]]
            syllabified_words[idx] = [s for s in syls]
            continue
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
    ipa_list = phonemize(
        syllable_tokens,
        language="fr-fr" if lang == "fr" else lang,
        backend="espeak",
        strip=True,
        preserve_punctuation=False,
        with_stress=False,
    )
    # post-processing of phonemize output
    ipa_list_fixed = []
    for ipa_syl in ipa_list:
        if ipa_syl == "(en)tuː(de)":
            ipa_list_fixed.append("toː")
        else:
            # Remove suprasegmentals that may still appear (like length markers)
            ipa_list_fixed.append(re.sub(r"[ː‿‖ ]", "", ipa_syl))
    # re-format such that ipa_list: list[list[str]],
    # where each list in the outer list is a word as a list of syllables
    ipa_list = []
    i = 0
    for word in syllabified_words:
        ipa_list.append([syl for syl in ipa_list_fixed[i : i + len(word)]])
        i += len(word)
    print(ipa_list)
    return ipa_list


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


def map_phoneme_sequences(phoneme_seq, phoneme_map) -> list[dict]:
    """
    Generate all possible language-specific phoneme combinations with weights and single_lang flag.

    Parameters:
        phoneme_seq (List[str]): Sequence of IPA phonemes (e.g., ["l", "j", "r"])
        phoneme_map (Dict[str, List[Dict[str, Any]]]): Mapping from IPA phonemes
            to a list of dicts with {"lang": ..., "ph": ..., "weight": ...}

    Returns:
        List[Dict[str, Any]]: Each dict has keys {"weight", "single_lang", "mapping"}.
    """

    # Step 1: restrict mapping to only relevant phonemes
    phoneme_seq_map = {ph: phoneme_map[ph] for ph in phoneme_seq if ph in phoneme_map}

    # Step 2: find maximum option length
    max_weight_all = max(len(options) for options in phoneme_seq_map.values())

    results = []

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

        single_lang = all(lang == langs[0] for lang in langs)

        results.append(
            {
                "weight": total_weight,
                "single_lang": single_lang,
                "mapping": mapping,
            }
        )

    return results


def choose_best_language(phoneme_seq, phoneme_map):
    """Choose the best language for a syllable, preferring only languages that can cover all phonemes."""
    lang_scores = {}
    coverage = {}

    for ph in phoneme_seq:
        if ph in phoneme_map:
            for idx, entry in enumerate(phoneme_map[ph]):
                lang = entry["lang"]
                base_score = 1 if idx == 0 else 0
                weight = entry.get("weight", 0)
                lang_scores[lang] = lang_scores.get(lang, 0) + base_score + weight
                coverage[lang] = coverage.get(lang, 0) + 1

    if not lang_scores:
        return None

    # nur Sprachen, die alle Phoneme der Silbe abdecken
    full_langs = {l for l, c in coverage.items() if c == len(phoneme_seq)}
    if full_langs:
        return max(full_langs, key=lambda l: lang_scores.get(l, float("-inf")))
    # Fallback: beste partielle (sollte selten auftreten)
    return max(lang_scores, key=lang_scores.get)


def map_syllable_with_alternatives(
    syllable,
    phoneme_map,
    key_lengths,
    alt_syllables=False,
    alt_phonemes=False,
    max_alts=0,
):
    """Map one IPA syllable into SV phonemes.
    Returns (main_lang, main_syllable, alt_syllables_list)."""

    phoneme_seq = segment_syllable(syllable, phoneme_map, key_lengths)

    # Beste Sprache nur aus solchen wählen, die volle Abdeckung haben
    main_lang = choose_best_language(phoneme_seq, phoneme_map)

    # Kandidaten pro Sprache sammeln (nur volle Abdeckung)
    lang_candidates = {}
    all_langs = {o["lang"] for ph in phoneme_seq for o in phoneme_map.get(ph, [])}

    for lang in all_langs:
        phones_per_pos = []
        valid = True
        for ph in phoneme_seq:
            opts = [o["ph"] for o in phoneme_map.get(ph, []) if o["lang"] == lang]
            if opts:
                phones_per_pos.append(opts)
            else:
                valid = False
                break

        # nur aufnehmen, wenn volle Abdeckung
        if valid and len(phones_per_pos) == len(phoneme_seq):
            lang_candidates[lang] = phones_per_pos

    # Helper: Silbe bauen; None zurückgeben, wenn Ergebnis leer
    def build_syllable(lang, phones_per_pos, allow_alt, max_alts=0):
        if not phones_per_pos or any(not opts for opts in phones_per_pos):
            return None
        parts = []
        for opts in phones_per_pos:
            if allow_alt and len(opts) > 1:
                if max_alts > 0:
                    opts = opts[: min(len(opts), max_alts + 1)]
                parts.append("[" + " | ".join(opts) + "]")
            else:
                parts.append(opts[0])
        seq = " ".join(parts).strip()
        if not seq:
            return None
        return f"<{lang}> {seq}"

    # Hauptsilbe (mit optionalen Phonem-Alternativen)
    main_syllable = None
    if main_lang in lang_candidates:
        main_syllable = build_syllable(
            main_lang, lang_candidates[main_lang], alt_phonemes, max_alts
        )

    # Fallback, falls main_lang keine volle Abdeckung hat (sehr selten)
    if main_syllable is None and lang_candidates:
        # nimm irgendeine gültige Sprache (die mit meisten Optionen)
        best_fallback_lang = max(
            lang_candidates.keys(),
            key=lambda L: sum(len(x) for x in lang_candidates[L]),
        )
        main_lang = best_fallback_lang
        main_syllable = build_syllable(
            main_lang, lang_candidates[best_fallback_lang], alt_phonemes, max_alts
        )

    # Wenn gar nichts ging: als Notnagel die rohe Sequenz ausgeben
    if main_syllable is None:
        import sys

        print(f"Warning: no full mapping for syllable '{syllable}'", file=sys.stderr)
        return None, " ".join(phoneme_seq), []

    # Alternative Silben
    alt_syllables_list = []
    if alt_syllables:
        scored = []
        for lang, phones_per_pos in lang_candidates.items():
            if lang == main_lang:
                continue
            syl = build_syllable(lang, phones_per_pos, alt_phonemes, max_alts)
            if syl is None:
                continue
            # Score: bevorzugt Sprachen mit weniger „Breite“ (nähere Entsprechung)
            # = Summe der Indexe 0-Annahme → je kleiner, desto besser.
            score = 0
            for ph in phoneme_seq:
                # Index der Sprache innerhalb des Mappings des Phonems (falls vorhanden)
                entries = [o for o in phoneme_map.get(ph, []) if o["lang"] == lang]
                if entries:
                    # wir werten Position 0 höher (näher)
                    score += 0 if entries.index(entries[0]) == 0 else 1
            scored.append((score, syl))

        # sortieren nach score, dann lexikographisch
        scored.sort(key=lambda x: (x[0], x[1]))

        # max_alts: 0 ⇒ alle; >0 ⇒ auf N begrenzen
        if max_alts > 0:
            scored = scored[: min(len(scored), max_alts + 1)]

        alt_syllables_list = [s for _, s in scored]

    return main_lang, main_syllable, alt_syllables_list


def ipa_to_sv(
    ipa_list,
    phoneme_map,
    key_lengths,
    alt_syllables=False,
    alt_phonemes=False,
    lang_per_phoneme=False,
    max_alts=0,
):
    """Convert IPA into SV phoneme sequence with optional alternatives."""

    output_words = []
    prev_lang = None

    for syllables in ipa_list:
        mapped = [
            map_syllable_with_alternatives(
                syl,
                phoneme_map,
                key_lengths,
                alt_syllables=alt_syllables,
                alt_phonemes=alt_phonemes,
                max_alts=max_alts,
            )
            for syl in syllables
            if syl
        ]

        word_out = []
        for main_lang, main_syllable, alt_sylls in mapped:
            if alt_syllables and alt_sylls:
                # Merge main syllable + alternatives into one bracketed group
                all_opts = [main_syllable] + alt_sylls
                word_out.append("[" + " | ".join(all_opts) + "]")
            else:
                # Insert language tag only when it changes
                if main_lang != prev_lang:
                    word_out.append(main_syllable)
                else:
                    # Skip repeating the tag, keep only the phoneme sequence
                    word_out.append(main_syllable.split(" ", 1)[1])
            prev_lang = main_lang

        # Join syllables with a single space
        output_words.append(" - ".join(word_out))

    # Join words with double spaces
    return "   ".join(output_words)


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
        "--alts",
        type=int,
        choices=[0, 1, 2, 3],
        default=0,
        help="Show alternatives. 0 = none, 1 = phonemes, 2 = syllables, 3 = both (default: 0)",
    )
    parser.add_argument(
        "-p",
        "--phoneme-edit",
        action="store_true",
        help="Allow language switching per phoneme instead of per syllable",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        type=int,
        default=0,
        help="Maximum number of alternatives shown in output. 0 = all (default: 0)",
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

    ipa_list = ipa_convert(text, args.lang)

    sv_phonemes = ipa_to_sv(
        ipa_list,
        phoneme_map,
        key_lengths,
        alt_syllables=args.alts > 2,
        alt_phonemes=args.alts in [1, 3],
        lang_per_phoneme=args.phoneme_edit,
        max_alts=args.verbose,
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(sv_phonemes)
    else:
        print(sv_phonemes)


if __name__ == "__main__":
    main()
