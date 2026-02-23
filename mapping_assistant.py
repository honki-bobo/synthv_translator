#!/usr/bin/env python3
"""
mapping_assistant.py - Interactive wizard for creating SynthV Translator mapping files.

Overview
--------
Creating a phoneme mapping file for a new language involves several steps that
require specialist knowledge: finding the right eSpeak language code, generating
text that covers all phonemes, running eSpeak to collect IPA output, and then
mapping each IPA symbol to the best-fitting phoneme(s) in one or more SynthV
voice languages.  This script automates every step through a guided 5-step
wizard so that the user only needs to make linguistic decisions, not technical
ones.

Wizard steps
------------
  1. Language selection  — search the eSpeak voice list, pick by number
  2. Coverage text       — paste (or supply via --coverage-file) text that
                           triggers all phonemes; eSpeak converts it to IPA
  3. vowels_orth         — enter the orthographic vowel characters for the
                           language (used by the translator for syllabification)
  4. Phoneme mapping     — for each extracted IPA symbol, accept the built-in
                           suggestion, edit it, or skip it
  5. Output path         — choose where to write the finished JSON file

Output format
-------------
The wizard writes a standard SynthV Translator mapping file:

    {
      "vowels_orth": "aeiouyąę",
      "ipa_process": [],          # empty — user fills in post-processing rules
      "word_prefs":  {},
      "syl_prefs":   {},
      "phoneme_map": {
        "a": [{"lang": "spanish", "ph": "a"}, ...],
        ...
      }
    }

Dependencies
------------
  Required  : espeak-ng (on PATH)
  Optional  : mappings/sv_phoneme_inventory.json  — enables phoneme validation
              mappings/ipa_suggestions.json        — enables built-in suggestions

Usage
-----
  python mapping_assistant.py
  python mapping_assistant.py --output mappings/pl.json
  python mapping_assistant.py --coverage-file coverage_pl.txt
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# ── Color output ───────────────────────────────────────────────────────────────
# ANSI colors are enabled when stdout is a real terminal.  On Windows they
# additionally require either Windows Terminal (WT_SESSION env var) or a
# third-party ANSI driver (ANSICON), because the classic cmd.exe console does
# not interpret ANSI escape sequences.

_color: bool = sys.stdout.isatty() and (
    os.name != "nt"
    or os.environ.get("WT_SESSION")   # Windows Terminal
    or os.environ.get("ANSICON")      # ConEmu / Cmder ANSI shim
)


def _c(code: str, text: str) -> str:
    """Wrap *text* in an ANSI SGR escape sequence identified by *code*.

    Falls back to plain text when color output is disabled so that the output
    is still readable when piped to a file or run in a non-color terminal.
    """
    return f"\033[{code}m{text}\033[0m" if _color else text


# Convenience wrappers — each applies a single SGR attribute to *t*.
def bold(t: str)   -> str: return _c("1",  t)   # bright / bold
def green(t: str)  -> str: return _c("32", t)   # success / accepted
def yellow(t: str) -> str: return _c("33", t)   # warning / skipped
def cyan(t: str)   -> str: return _c("36", t)   # interactive prompts
def dim(t: str)    -> str: return _c("2",  t)   # secondary information
def red(t: str)    -> str: return _c("31", t)   # errors


# ── IPA suggestion data (loaded from file) ─────────────────────────────────────
# These module-level dicts are intentionally empty at import time.
# load_ipa_suggestions() fills them from mappings/ipa_suggestions.json, which
# is a committed data file containing best-guess SynthV phoneme alternatives for
# ~90 common IPA symbols.
#
# Keeping them as plain dicts (rather than constants) allows the loader to
# replace the contents in-place without requiring callers to import the loader.

IPA_SUGGESTIONS: dict[str, list[dict]] = {}
"""Maps each IPA symbol to a best-first list of SynthV phoneme alternatives.

Each entry in the list is a dict with keys ``lang`` (SynthV language name,
e.g. ``"english"``) and ``ph`` (phoneme token, e.g. ``"ay"``), and an
optional ``weight`` (float, default 1.0).  Example::

    "aɪ": [{"lang": "english", "ph": "ay"}, {"lang": "spanish", "ph": "a i"}]

A space in ``ph`` means the IPA symbol maps to two consecutive SynthV phonemes.
"""

IPA_DESCRIPTIONS: dict[str, str] = {}
"""Maps IPA symbols to short English descriptions shown during Step 4.

Example::

    "ɲ": "palatal nasal (as in Spanish 'año')"
"""


def load_ipa_suggestions() -> bool:
    """Populate IPA_SUGGESTIONS and IPA_DESCRIPTIONS from the data file.

    Reads ``mappings/ipa_suggestions.json`` (relative to this script) and
    updates the two module-level dicts.  The file must have the structure::

        {
          "suggestions":  { "<ipa>": [{"lang": "...", "ph": "..."}, ...], ... },
          "descriptions": { "<ipa>": "short description", ... }
        }

    Returns True if the file was loaded successfully, False otherwise.
    Missing keys in the JSON are treated as empty dicts rather than errors,
    so a file that only contains ``suggestions`` is still valid.
    """
    global IPA_SUGGESTIONS, IPA_DESCRIPTIONS
    path = Path(__file__).parent / "mappings" / "ipa_suggestions.json"
    if not path.exists():
        return False
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        IPA_SUGGESTIONS = data.get("suggestions", {})
        IPA_DESCRIPTIONS = data.get("descriptions", {})
        return True
    except Exception:
        return False


# ── Utilities ──────────────────────────────────────────────────────────────────

def run_command(args: list[str]) -> tuple[str, str, int]:
    """Run a subprocess and return (stdout, stderr, returncode).

    Uses UTF-8 decoding with ``errors="replace"`` so that unexpected bytes in
    eSpeak output (e.g. from voice files with non-standard encodings) do not
    raise an exception — they are replaced with the Unicode replacement
    character instead.

    Returns a tuple of ``(stdout, stderr, returncode)``.  If the executable is
    not found on PATH, returns ``("", "Command not found: <name>", 1)`` so that
    callers can handle the error uniformly without catching exceptions.
    """
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        return result.stdout, result.stderr, result.returncode
    except FileNotFoundError:
        return "", f"Command not found: {args[0]}", 1


def clean_ipa(text: str) -> str:
    """Strip prosodic and diacritical markers from eSpeak IPA output.

    eSpeak annotates its IPA output with markers that encode prosodic
    information (stress, length, pitch) but are not part of the underlying
    phoneme inventory.  Keeping them would cause ``extract_ipa_symbols`` to
    produce spurious symbols (e.g. ``ˈa`` instead of ``a``).

    Removed markers:
      - ``ˈ``  primary stress (U+02C8)
      - ``ˌ``  secondary stress (U+02CC)
      - ``ː``  length mark (U+02D0)
      - ``ˑ``  half-length mark (U+02D1)
      - combining diacritics U+0300–U+036F (acute, grave, tilde, etc.)
      - ``̯``   non-syllabic combining mark (U+032F)
      - ``.``   syllable boundary dot used by some eSpeak versions

    Whitespace is normalised to single spaces so that downstream string
    scanning is unambiguous.
    """
    # Remove suprasegmental markers: stress and length
    for ch in "ˈˌːˑ":
        text = text.replace(ch, "")
    # Remove combining diacritics (U+0300–U+036F) and the non-syllabic mark
    text = re.sub(r"[\u0300-\u036f\u032f]", "", text)
    # Remove intra-word syllable boundary dots that appear between two
    # non-whitespace characters (e.g. "ˈpɪ.ti" → "pɪti")
    text = re.sub(r"(?<=[^\s])\.(?=[^\s])", "", text)
    # Collapse multiple spaces / newlines into a single space
    return re.sub(r"\s+", " ", text).strip()


def extract_ipa_symbols(clean_text: str) -> list[str]:
    """Extract the sorted, unique set of IPA symbols from cleaned eSpeak output.

    Uses a **longest-match** greedy scan: multi-character sequences that appear
    as keys in IPA_SUGGESTIONS (e.g. ``tʃ``, ``aɪ``) are matched before their
    constituent characters.  This prevents ``tʃ`` from being split into ``t``
    and ``ʃ`` or ``aɪ`` from being split into ``a`` and ``ɪ``.

    Algorithm:
      1. Build a list of all multi-character IPA_SUGGESTIONS keys, sorted by
         length descending so that longer sequences are tried first.
      2. Scan left-to-right through ``clean_text``.  At each position:
           a. Try each multi-char sequence in order; consume it on the first match.
           b. If no multi-char sequence matches, consume a single character.
      3. Discard tokens that are entirely digits or non-word characters (e.g.
         punctuation that slips through eSpeak output like ``|`` or ``-``).

    Returns a list of symbols sorted first by length (shorter first) then
    lexicographically, so that the display in Step 2 is consistent.
    """
    # Pre-sort multi-character keys longest-first to ensure greedy matching
    multi_seqs = sorted(
        [k for k in IPA_SUGGESTIONS if len(k) > 1],
        key=len,
        reverse=True,
    )
    skip = set(" \t\n\r")   # whitespace is not a phoneme symbol
    symbols: set[str] = set()
    i = 0
    while i < len(clean_text):
        if clean_text[i] in skip:
            i += 1
            continue
        matched = False
        # Try all multi-character sequences at the current position
        for seq in multi_seqs:
            if clean_text[i : i + len(seq)] == seq:
                symbols.add(seq)
                i += len(seq)
                matched = True
                break
        if not matched:
            # No multi-char match — consume a single character
            symbols.add(clean_text[i])
            i += 1
    # Remove digits and standalone punctuation that are not IPA symbols
    symbols = {s for s in symbols if not re.fullmatch(r"[0-9\W]+", s)}
    return sorted(symbols, key=lambda s: (len(s), s))


def format_alternatives(alts: list[dict]) -> str:
    """Render a list of phoneme alternatives as a human-readable string.

    Example input::

        [{"lang": "english", "ph": "ay"}, {"lang": "spanish", "ph": "a i", "weight": 0.5}]

    Example output::

        "english:ay  spanish:a i:0.5"

    The output format mirrors the input syntax accepted by
    ``parse_mapping_input`` so that it can serve as a prompt hint.
    """
    parts = []
    for alt in alts:
        w = alt.get("weight")
        parts.append(f"{alt['lang']}:{alt['ph']}" + (f":{w}" if w else ""))
    return "  ".join(parts)


def parse_mapping_input(user_input: str) -> list[dict] | None:
    """Parse a user-typed mapping string into a list of alternative dicts.

    Expected format (whitespace-separated tokens)::

        lang:phoneme[:weight]  lang:phoneme[:weight]  ...

    Examples::

        "english:ay"                  → [{"lang": "english", "ph": "ay"}]
        "spanish:a  english:aa:0.5"   → [{"lang": "spanish", "ph": "a"},
                                          {"lang": "english", "ph": "aa", "weight": 0.5}]
        "english:t s"                 → invalid (space inside token is a separator)

    Note: A SynthV phoneme that consists of two tokens (e.g. ``t s`` for the
    lateral fricative ɬ) must be entered as a single colon-separated field:
    ``english:t s`` is invalid because the space splits it into two tokens.
    Use ``english:t`` and add a second entry instead, or enter it as
    ``"english:t s"`` without inner quotes — the ``ph`` value may contain
    spaces; only the colon separates fields.

    Returns the list of dicts, or ``None`` if any token is malformed.
    """
    alts = []
    for token in user_input.strip().split():
        parts = token.split(":")
        # Each token must have at least lang and ph (the first two colon-parts)
        if len(parts) < 2 or not parts[0] or not parts[1]:
            return None
        alt: dict = {"lang": parts[0], "ph": parts[1]}
        if len(parts) >= 3:
            try:
                alt["weight"] = float(parts[2])
            except ValueError:
                return None
        alts.append(alt)
    return alts if alts else None


def load_sv_inventory() -> dict | None:
    """Load the SynthV phoneme inventory from mappings/sv_phoneme_inventory.json.

    The inventory is generated by ``generate_phoneme_inventory.py`` and
    contains all phonemes supported by each SynthV voice language, grouped
    by notation system and phoneme category.  It is used here only for
    validation (warning the user when they enter a phoneme that does not
    exist in the target language).

    Returns the parsed JSON dict, or ``None`` if the file does not exist or
    cannot be parsed.  The wizard continues normally if ``None`` is returned —
    validation is advisory, not blocking.
    """
    path = Path(__file__).parent / "mappings" / "sv_phoneme_inventory.json"
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def build_flat_inventory(inventory: dict) -> dict[str, set[str]]:
    """Flatten the nested SynthV phoneme inventory to ``{language: {phoneme, …}}``.

    The raw inventory from ``sv_phoneme_inventory.json`` has three levels of
    nesting::

        {
          "arpabet": {
            "english": {
              "vowel":     ["aa", "ae", ...],
              "consonant": ["b", "ch", ...],
              ...
            }
          },
          "romaji": { "japanese": { ... } },
          ...
        }

    This function collapses notation systems and phoneme categories so that
    membership testing becomes a simple ``phoneme in flat_inv[lang]`` lookup,
    which is all the wizard needs for validation.

    The top-level ``"common"`` key (silence, breath, etc.) is implicitly
    skipped because its value is a plain list rather than a dict of languages.
    """
    flat: dict[str, set[str]] = {}
    for _notation, langs in inventory.items():
        # Skip entries that are not dicts of languages (e.g. the "common" key)
        if not isinstance(langs, dict):
            continue
        for lang, categories in langs.items():
            if not isinstance(categories, dict):
                continue
            flat.setdefault(lang, set())
            # Merge all phoneme categories (vowel, consonant, diphthong, …)
            for phonemes in categories.values():
                flat[lang].update(phonemes)
    return flat


def check_pyphen(lang_code: str) -> bool:
    """Return True if pyphen has a hyphenation dictionary for *lang_code*.

    pyphen uses ISO 639 codes with an optional region suffix, e.g. ``de``,
    ``de_DE``, ``pl``, ``fr_FR``.  eSpeak codes may include a script or
    dialect marker (e.g. ``cmn``, ``de-be``) that pyphen does not recognise,
    so we try several normalised variants before giving up:

      1. The raw eSpeak code as-is (handles ``pl``, ``de`` directly)
      2. The code with hyphens replaced by underscores (pyphen uses underscores)
      3. A ``ll_CC`` form derived from the base language tag (e.g. ``de_DE``)
      4. The bare ISO 639-1 / 639-3 base code only (e.g. ``de``)

    Returns False if pyphen is not installed or if none of the tried code
    variants appear in ``pyphen.LANGUAGES``.
    """
    try:
        import pyphen

        base = re.split(r"[-_]", lang_code)[0]   # "de-be" → "de", "cmn" → "cmn"
        for code in [
            lang_code,                    # raw eSpeak code
            lang_code.replace("-", "_"),  # hyphen → underscore
            f"{base}_{base.upper()}",     # "de" → "de_DE"
            base,                         # bare base code
        ]:
            if code in pyphen.LANGUAGES:
                return True
        return False
    except ImportError:
        return False


def validate_phoneme(ph_token: str, lang: str, flat_inv: dict[str, set[str]]) -> bool:
    """Return True if every phoneme in *ph_token* is valid for *lang*.

    *ph_token* may be a single phoneme (``"ay"``) or a space-separated
    sequence (``"t s"``), since some IPA symbols map to two consecutive SynthV
    phonemes.  Each individual part is looked up in the flat inventory.

    If *lang* is not in ``flat_inv`` (e.g. the user typed a language name that
    the locally-generated inventory does not cover), the function returns
    ``True`` rather than a false negative — the user may be targeting a voice
    language that was not installed on the machine used to generate the inventory.
    """
    if lang not in flat_inv:
        return True  # Cannot validate — treat as valid to avoid false warnings
    for token in ph_token.split():
        if token not in flat_inv[lang]:
            return False
    return True


# ── Wizard steps ───────────────────────────────────────────────────────────────

def step_check_espeak() -> bool:
    """Verify that espeak-ng is available on PATH.

    Runs ``espeak-ng --version`` as a quick availability check.  If the
    command fails (non-zero exit code or executable not found), prints
    platform-specific install instructions and returns False so that
    ``main()`` can exit early before any interactive prompts are shown.

    Returns True if espeak-ng responds successfully.
    """
    _, _, rc = run_command(["espeak-ng", "--version"])
    if rc != 0:
        print(red("  ERROR: espeak-ng is not installed or not on PATH."))
        print("  Install it:")
        print("    Windows : https://github.com/espeak-ng/espeak-ng/releases")
        print("    macOS   : brew install espeak-ng")
        return False
    return True


def step_select_language() -> tuple[str, str]:
    """Interactively select an eSpeak language code by searching the voice list.

    Runs ``espeak-ng --voices`` and parses the tabular output, which has the
    format::

        Pty  Language       Gender  VoiceName          File
         5   pl             M       polish             other/pl
         5   pl-pl          M       polish             other/pl

    Columns are whitespace-separated; we extract column 1 (language code,
    0-indexed) and column 3 (voice name).

    The search term is matched case-insensitively against both the language
    code and the voice name, so ``"polish"``, ``"pl"``, and ``"pol"`` all find
    the same entry.  Up to 20 matches are displayed; the user picks by number
    or refines their search.

    Returns a ``(lang_code, voice_name)`` tuple for the chosen voice.
    """
    print(bold("\n[Step 1/5] Select Language"))
    print("Search for a language by name or code (e.g. 'polish', 'pl', 'czech').")

    while True:
        search = input(cyan("  Search: ")).strip().lower()
        if not search:
            continue

        stdout, _, rc = run_command(["espeak-ng", "--voices"])
        if rc != 0:
            print(red("  Could not list eSpeak voices. Is espeak-ng installed?"))
            sys.exit(1)

        matches: list[tuple[str, str]] = []
        for line in stdout.splitlines():
            line = line.strip()
            # Skip empty lines and the header row ("Pty  Language …")
            if not line or line.startswith("Pty"):
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            lang_code, voice_name = parts[1], parts[3]
            if search in lang_code.lower() or search in voice_name.lower():
                matches.append((lang_code, voice_name))

        if not matches:
            print(yellow(f"  No voices found matching '{search}'. Try again."))
            continue

        print(f"\n  Found {len(matches)} match(es):")
        shown = matches[:20]   # cap the list to avoid flooding the terminal
        for i, (code, name) in enumerate(shown, 1):
            print(f"    {dim(str(i)+'.')}  {bold(code):20} {name}")
        if len(matches) > 20:
            print(dim(f"    ... and {len(matches) - 20} more. Refine your search."))

        choice = input(cyan("\n  Enter number to select, or press Enter to search again: ")).strip()
        if not choice:
            continue
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(shown):
                code, name = shown[idx]
                print(green(f"  Selected: {code} ({name})"))
                return code, name
        except ValueError:
            pass
        print(yellow("  Invalid selection. Try again."))


def step_coverage_text(lang_code: str, prefilled_text: str = "") -> list[str]:
    """Run a coverage text through eSpeak and return all unique IPA symbols found.

    The goal is to produce a comprehensive list of IPA symbols that eSpeak
    generates for the target language so that the mapping step covers every
    phoneme that might appear in real input.  The function supports iterative
    refinement: the user can run eSpeak on multiple texts in sequence, with
    newly discovered symbols added to the running set each time.

    Args:
        lang_code:      The eSpeak language code selected in Step 1.
        prefilled_text: Optional text loaded from a ``--coverage-file``; if
                        provided it is processed automatically on the first
                        iteration without showing the paste prompt.

    Returns a sorted list of unique IPA symbol strings after the user is
    satisfied with the coverage.

    Algorithm:
      1. Accept text (from file or interactive paste).
      2. Run ``espeak-ng -v <lang> --ipa -q`` on the text.
      3. Call ``clean_ipa()`` to strip prosodic markers.
      4. Call ``extract_ipa_symbols()`` to tokenise the cleaned IPA.
      5. Merge new symbols into the accumulated set.
      6. Show the running total and highlight any symbols without a built-in
         suggestion; let the user continue or add more text.
    """
    print(bold("\n[Step 2/5] Extract IPA Symbols from Coverage Text"))
    if not prefilled_text:
        print("Paste a text that covers all phonemes of the language.")
        print(dim("  It doesn't need to make sense — just cover as many sounds as possible."))
        print(dim("  Tip: Ask an AI with this prompt:"))
        print(dim(f'  "Give me a list of {lang_code} words covering all distinct IPA phonemes,'))
        print(dim(f'  including rare sounds like affricates, palatal consonants, and rare vowels."'))
    print()

    # All IPA symbols collected so far across all text iterations
    accumulated: set[str] = set()
    first_iteration = True

    while True:
        if first_iteration and prefilled_text:
            # Use the pre-loaded file content on the first pass without prompting
            text = prefilled_text
            first_iteration = False
        else:
            first_iteration = False
            print("Paste coverage text (press Enter on an empty line when done):")
            lines = []
            while True:
                try:
                    line = input()
                except EOFError:
                    # Handle piped input gracefully
                    break
                if line == "":
                    break
                lines.append(line)
            text = " ".join(lines).strip()

        if not text:
            if accumulated:
                # The user pressed Enter without adding text — treat as done
                break
            print(yellow("  No text entered. Please paste some text."))
            continue

        print(f"\n  Running eSpeak ({lang_code})...")
        stdout, stderr, rc = run_command(["espeak-ng", "-v", lang_code, "--ipa", "-q", text])

        if rc != 0 or not stdout.strip():
            print(red(f"  eSpeak failed: {stderr.strip() or 'no output produced'}"))
            retry = input("  Try again with different text? [Y/n]: ").strip().lower()
            if retry == "n":
                if not accumulated:
                    sys.exit(1)
                break
            continue

        # Process the IPA output and merge into the accumulated set
        cleaned = clean_ipa(stdout)
        new_symbols = extract_ipa_symbols(cleaned)
        before = len(accumulated)
        accumulated.update(new_symbols)
        added = len(accumulated) - before

        symbols = sorted(accumulated, key=lambda s: (len(s), s))
        print(f"\n  {green('✓')} Total unique IPA symbols: {bold(str(len(symbols)))}"
              + (f"  ({added} new)" if added else "  (no new symbols found)"))
        print(f"  {' '.join(bold(s) for s in symbols)}")

        # Highlight symbols that have no entry in IPA_SUGGESTIONS — they will
        # need to be mapped manually in Step 4
        unknown = [s for s in symbols if s not in IPA_SUGGESTIONS]
        if unknown:
            print(yellow(f"\n  {len(unknown)} symbol(s) have no built-in suggestion:"), end=" ")
            print(yellow(" ".join(unknown)))
            print(dim("  You will be prompted to map these manually."))

        action = input(cyan("\n  [Enter] Proceed  [a] Add more text: ")).strip().lower()
        if action != "a":
            return symbols


def step_vowels_orth() -> str:
    """Ask the user for the orthographic vowel characters of the language.

    ``vowels_orth`` is a string containing every character in the target
    language's writing system that represents a vowel sound.  The SynthV
    Translator uses it as a fallback when pyphen is not available for the
    language: it counts vowel characters to estimate syllable boundaries and
    therefore determine how many SynthV notes a multi-syllabic word should be
    split across.

    The string should include:
      - all base vowel letters (a, e, i, o, u for most languages)
      - accented / modified forms (ä, ö, ü, à, é, ę, ą, …)
      - digraphs are NOT included — only individual characters

    Returns the non-empty string entered by the user.
    """
    print(bold("\n[Step 3/5] Orthographic Vowels"))
    print("Enter all characters used to write vowel sounds in this language.")
    print(dim("  Include base vowels and all accented/special forms."))
    print(dim("  This is used for syllabification — not for phoneme mapping."))
    print(dim("  Examples:"))
    print(dim("    German  : aeiouyäöüÿ"))
    print(dim("    French  : aeiouyàâäéèêëïîôùûüœæ"))
    print(dim("    Polish  : aeiouyąę"))
    print(dim("    Russian : аеёиоуыэюя"))
    print()

    while True:
        value = input(cyan("  vowels_orth: ")).strip()
        if value:
            print(green(f'  Set: "{value}"'))
            return value
        print(yellow("  Please enter at least the basic vowels (e.g. aeiou)."))


def step_map_phonemes(symbols: list[str], flat_inv: dict[str, set[str]]) -> dict:
    """Interactively confirm or edit a SynthV phoneme mapping for each IPA symbol.

    For each symbol in *symbols* the wizard displays:
      - its index in the sequence (``[n/total]``)
      - the IPA symbol in bold
      - a short phonetic description (from IPA_DESCRIPTIONS) if available
      - the best-guess suggestion from IPA_SUGGESTIONS, formatted with
        ``format_alternatives()`` and shown in green, or a yellow notice if
        no suggestion exists

    The user can then:
      - Press **Enter** to accept the suggestion as-is
      - Type **e** to open an edit prompt and enter a custom mapping
      - Type a mapping directly (``lang:ph[:weight] …``) without pressing ``e``
      - Type **s** to skip the symbol (it will be absent from the output dict)
      - Type **q** to stop and save progress so far
      - Type **?** to see a format reminder

    Phonemes entered manually are validated against the flat inventory if one
    was loaded; a warning is printed but the value is still accepted.

    Args:
        symbols:  Sorted list of IPA symbols from Step 2.
        flat_inv: Flat phoneme inventory for validation, or an empty dict.

    Returns the ``phoneme_map`` dict (only symbols that were confirmed or
    manually set — skipped symbols are excluded).
    """
    print(bold("\n[Step 4/5] Map Phonemes"))
    print("Confirm or edit the suggested SynthV mapping for each IPA symbol.")
    print(dim("  Input format:  lang:phoneme[:weight]  (space-separated pairs)"))
    print(dim("  Example:       spanish:a  english:aa:0.5"))
    print(dim("  Languages:     english, spanish, japanese, mandarin, cantonese, korean"))
    print(dim("  Commands:      Enter=accept  e=edit  s=skip  q=quit  ?=help"))
    print()

    phoneme_map: dict = {}
    total = len(symbols)

    for idx, symbol in enumerate(symbols, 1):
        suggestion = IPA_SUGGESTIONS.get(symbol)
        # Try to find a description for the symbol; if it has a length mark
        # (ː), also try the base form (e.g. "eː" → fall back to "e")
        desc = IPA_DESCRIPTIONS.get(symbol) or IPA_DESCRIPTIONS.get(symbol.rstrip("ː"), "")

        print(f"  {dim('─' * 56)}")
        header = f"  [{idx}/{total}]  {bold(symbol)}"
        if desc:
            header += f"   {dim(desc)}"
        print(header)

        if suggestion:
            print(f"  Suggestion: {green(format_alternatives(suggestion))}")
        else:
            print(f"  {yellow('No built-in suggestion — enter mapping manually.')}")

        while True:
            # Tailor the prompt hint based on whether a suggestion is available
            if suggestion:
                prompt = f"  {dim('[Enter] accept  [e] edit  [s] skip  [q] quit  [?] help')}  > "
            else:
                prompt = f"  {dim('[s] skip  [q] quit  [?] help')}  mapping > "

            raw = input(cyan(prompt)).strip()

            if raw == "" and suggestion:
                # Accept the built-in suggestion unchanged
                phoneme_map[symbol] = suggestion
                print(f"  {green('✓')} Accepted")
                break

            elif raw == "" and not suggestion:
                # Cannot accept nothing when there is no suggestion to fall back on
                print(red("  Please enter a mapping or type 's' to skip."))

            elif raw.lower() == "s":
                # Skip — symbol will be absent from phoneme_map; user may add it later
                print(f"  {yellow('Skipped')} — add to phoneme_map manually later if needed")
                break

            elif raw.lower() == "q":
                # Early exit — save progress so far and let main() finish writing the file
                print(yellow("\n  Stopping. Progress so far will be saved."))
                return phoneme_map

            elif raw.lower() == "?":
                print(dim("  Format: lang:phoneme[:weight] pairs separated by spaces"))
                print(dim("  Weight is optional (higher = more preferred by optimizer)"))
                print(dim("  Example: english:sh:2.0 japanese:sh"))

            elif raw.lower() == "e":
                # Explicit edit mode — re-prompt for the mapping
                raw2 = input(cyan("  New mapping > ")).strip()
                parsed = parse_mapping_input(raw2)
                if parsed is None:
                    print(red("  Invalid format. Try again."))
                    continue
                _warn_unknown_phonemes(parsed, flat_inv)
                phoneme_map[symbol] = parsed
                print(f"  {green('✓')} Set: {format_alternatives(parsed)}")
                break

            else:
                # Try to parse the raw input directly as a mapping string
                parsed = parse_mapping_input(raw)
                if parsed is None:
                    print(red("  Invalid format. Use: lang:phoneme[:weight] ..."))
                    continue
                _warn_unknown_phonemes(parsed, flat_inv)
                phoneme_map[symbol] = parsed
                print(f"  {green('✓')} Set: {format_alternatives(parsed)}")
                break

    return phoneme_map


def _warn_unknown_phonemes(alts: list[dict], flat_inv: dict[str, set[str]]) -> None:
    """Print a warning for each phoneme token not found in the SV inventory.

    This is called after the user enters or edits a mapping.  The check is
    advisory: an unknown phoneme produces a warning but is still accepted, so
    the user can create mappings for voice languages that were not installed on
    the machine used to generate the inventory.

    Silently does nothing if *flat_inv* is empty (no inventory was loaded).

    Args:
        alts:     The list of alternative dicts just entered by the user.
        flat_inv: Flat phoneme inventory from ``build_flat_inventory``.
    """
    if not flat_inv:
        return  # No inventory loaded — skip validation entirely
    for alt in alts:
        lang, ph = alt["lang"], alt["ph"]
        if not validate_phoneme(ph, lang, flat_inv):
            print(yellow(f"  Warning: '{ph}' not found in {lang} phoneme inventory."))
            print(dim("  Check mappings/sv_phoneme_inventory.json for valid phonemes."))


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    """Entry point for the mapping assistant wizard.

    Parses CLI arguments, runs pre-flight checks, then executes the five wizard
    steps in order.  After all steps complete (or the user quits Step 4 early),
    it assembles and writes the mapping JSON file and prints a summary.

    CLI arguments:
      --output / -o FILE      Write the mapping file to FILE instead of
                              prompting for a path in Step 5.
      --coverage-file / -c FILE
                              Load coverage text from FILE instead of prompting
                              in Step 2.  The file must be UTF-8 encoded plain
                              text.
    """
    parser = argparse.ArgumentParser(
        description="Interactive wizard for creating SynthV Translator mapping files."
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file path (default: mappings/<lang_code>.json)",
    )
    parser.add_argument(
        "--coverage-file", "-c",
        type=str,
        metavar="FILE",
        help="Path to a text file containing the coverage text (skips the paste prompt).",
    )
    args = parser.parse_args()

    # Load the coverage file content up-front so we can report a missing-file
    # error before showing the welcome banner, not buried mid-wizard
    prefilled_text = ""
    if args.coverage_file:
        coverage_path = Path(args.coverage_file)
        if not coverage_path.exists():
            print(red(f"  ERROR: Coverage file not found: {coverage_path}"))
            sys.exit(1)
        prefilled_text = coverage_path.read_text(encoding="utf-8")

    print(bold("=" * 56))
    print(bold("  SynthV Translator — Mapping File Assistant"))
    print(bold("=" * 56))
    print(dim("  This wizard creates a phoneme mapping file for"))
    print(dim("  a new language step by step."))

    # ── Pre-flight checks ──────────────────────────────────────────────────────
    # Verify espeak-ng is available before showing any interactive prompts
    if not step_check_espeak():
        sys.exit(1)

    # Load the SynthV phoneme inventory for optional validation in Step 4.
    # The wizard works without it, but with it we can warn about typos.
    inventory = load_sv_inventory()
    flat_inv = build_flat_inventory(inventory) if inventory else {}
    if inventory:
        print(dim(f"  SV phoneme inventory loaded ({len(flat_inv)} languages)."))
    else:
        print(dim("  No SV phoneme inventory found. Run generate_phoneme_inventory.py"))
        print(dim("  for phoneme validation during mapping."))

    # Load the IPA suggestions table.  This file is committed to the repository
    # so it should always be present; warn if it is somehow missing.
    if not load_ipa_suggestions():
        print(yellow("  Warning: mappings/ipa_suggestions.json not found."))
        print(yellow("  Phoneme suggestions will be unavailable."))

    # ── Step 1: Language ───────────────────────────────────────────────────────
    lang_code, lang_name = step_select_language()

    # Inform the user whether pyphen can assist with syllabification.
    # This is purely informational — the translator works either way.
    if check_pyphen(lang_code):
        print(green(f"  pyphen: dictionary available for '{lang_code}'"))
    else:
        print(yellow(f"  pyphen: no dictionary for '{lang_code}'"))
        print(dim("  Syllabification will rely on vowels_orth only."))

    # ── Step 2: Coverage text → IPA symbols ───────────────────────────────────
    symbols = step_coverage_text(lang_code, prefilled_text)

    # ── Step 3: vowels_orth ────────────────────────────────────────────────────
    vowels_orth = step_vowels_orth()

    # ── Step 4: Map phonemes ───────────────────────────────────────────────────
    phoneme_map = step_map_phonemes(symbols, flat_inv)

    # Assemble the mapping file structure.  ipa_process, word_prefs, and
    # syl_prefs are left empty — the user can add them manually after reviewing
    # the output file.  See MAPPING_GUIDE.md for details on each field.
    mapping = {
        "vowels_orth": vowels_orth,
        "ipa_process": [],   # post-processing rules to normalise eSpeak variants
        "word_prefs":  {},   # per-word phoneme overrides
        "syl_prefs":   {},   # per-syllable phoneme overrides
        "phoneme_map": phoneme_map,
    }

    # ── Step 5: Output path ────────────────────────────────────────────────────
    default_path = Path(__file__).parent / "mappings" / f"{lang_code}.json"
    if args.output:
        output_path = Path(args.output)
    else:
        print(bold("\n[Step 5/5] Output File"))
        print(f"  Where should the mapping file be saved?")
        raw = input(cyan(f"  Path [{dim(str(default_path))}]: ")).strip()
        output_path = Path(raw) if raw else default_path

    # Create any missing parent directories (e.g. if --output uses a new path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)

    # ── Summary ────────────────────────────────────────────────────────────────
    skipped = [s for s in symbols if s not in phoneme_map]
    print(bold("\n" + "=" * 56))
    print(green(bold("  Done!")))
    print(bold("=" * 56))
    print(f"\n  File written : {bold(str(output_path))}")
    print(f"  Mapped       : {bold(str(len(phoneme_map)))}/{len(symbols)} symbols")

    if skipped:
        print(yellow(f"  Skipped      : {' '.join(skipped)}"))
        print(dim("  Add these to phoneme_map in the output file manually."))

    print(f"\n  To test your mapping:")
    print(f"  python synthv_translator.py -l {lang_code} -m {output_path} \"test text\"")
    print(dim("\n  Tip: If eSpeak produces inconsistent variants of the same sound"))
    print(dim("  (e.g. both 'r' and 'ɾ'), add ipa_process rules to normalise them."))
    print(dim("  See MAPPING_GUIDE.md for details."))
    print()


if __name__ == "__main__":
    main()
