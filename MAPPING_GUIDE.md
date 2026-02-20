# Phoneme Mapping Guide

This guide explains how phoneme mapping works in Synthesizer V Translator and how to create or modify mapping files.

## Table of Contents

- [Understanding Phoneme Mapping](#understanding-phoneme-mapping)
- [Mapping File Structure](#mapping-file-structure)
  - [vowels_orth](#section-1-vowels_orth)
  - [ipa_process](#section-2-ipa_process)
  - [word_prefs](#section-3-word_prefs-optional)
  - [syl_prefs](#section-4-syl_prefs-optional)
  - [phoneme_map](#section-5-phoneme_map)
- [IPA to SynthV Conversion](#ipa-to-synthv-conversion)
- [Weighting System](#weighting-system)
- [Creating a New Mapping](#creating-a-new-mapping)
- [Testing and Refinement](#testing-and-refinement)
- [Reference Tables](#reference-tables)

## Understanding Phoneme Mapping

### The Translation Pipeline

```
Input Text → eSpeak (IPA) → Mapping File → SynthV Phonemes
```

1. **Input**: Text in source language (e.g., "Hallo")
2. **eSpeak**: Converts to IPA phonemes (e.g., "halo")
3. **Mapping**: IPA → SynthV phonemes using mapping file
4. **Output**: SynthV format (e.g., "<spanish> h a - l o")

### Why Mapping is Needed

- **eSpeak outputs IPA**: International Phonetic Alphabet (universal)
- **SynthV uses language-specific notations**: ARPABET (English), X-SAMPA (Spanish), Romaji (Japanese), etc.
- **Mapping bridges the gap**: Converts universal IPA to SynthV's format

## Mapping File Structure

A mapping file is a JSON file with five sections (three required, two optional):

```json
{
  "vowels_orth": "aeiouyäöü",
  "ipa_process": [
    ["pattern", "replacement"]
  ],
  "word_prefs": {
    "frühling": "<mandarin> f 7 y - <cantonese> l I N"
  },
  "syl_prefs": {
    "schön": "<english> sh ey uw"
  },
  "phoneme_map": {
    "ipa_phoneme": [
      {"lang": "language", "ph": "synthv_phoneme", "weight": 2.0}
    ]
  }
}
```

### Section 1: vowels_orth

**Purpose**: Defines orthographic vowels for syllabification

```json
"vowels_orth": "aeiouyäöüÿ"
```

- Lists all characters considered vowels in the source language
- Used by pyphen for syllable boundary detection
- Include accented/special vowels (ä, é, ø, etc.)

**Examples:**
- German: `"aeiouyäöüÿ"`
- French: `"aeiouyàâäéèêëïîôùûü"`
- Polish: `"aeiouyąęó"`

### Section 2: ipa_process

**Purpose**: Post-process IPA output from eSpeak using regex

```json
"ipa_process": [
  ["([^aeiouyäöüɛɔœøɐəɜ])(ɾ|r)", "\\1ʁ"],
  ["^(ɾ|r)", "ʁ"]
]
```

Each entry is a `[pattern, replacement]` pair using Python regex syntax.

**Use cases:**
- **Standardizing variants**: Convert 'r' variants to preferred form
- **Fixing eSpeak quirks**: Adjust eSpeak's specific output
- **Dialect adaptation**: Apply language-specific phonological rules

**Example - German R-sound:**
```json
["([^aeiouyäöüɛɔœøɐəɜ])(ɾ|r)", "\\1ʁ"]
```
Changes [r] or [ɾ] after consonants to [ʁ] (uvular fricative).

### Section 3: word_prefs (optional)

**Purpose**: Override the entire translation output for specific words

```json
"word_prefs": {
    "frühling": "<mandarin> f 7 y - <cantonese> l I N",
    "deutschland": "<spanish> d o e u t sh - <english> l ae n d"
}
```

- Keys are **case-insensitive** (e.g. `"frühling"` matches "Frühling" in the input)
- Values use the same format as the translator output: `<language> phoneme ...`, syllables separated by ` - `
- Values can contain multiple language switches within a single syllable (e.g. `<english> ch <spanish> a o`)
- When a word matches, the automatic translation is completely replaced by the preference
- Takes **precedence** over `syl_prefs` for the same word

Use this when you've found a better phoneme sequence for an entire word through manual experimentation in Synthesizer V.

### Section 4: syl_prefs (optional)

**Purpose**: Override the translation output for specific syllables

```json
"syl_prefs": {
    "früh": "<mandarin> f 7 y",
    "ling": "<cantonese> l I N",
    "schön": "<english> sh ey uw"
}
```

- Keys are **case-insensitive** and matched against orthographic syllables after syllabification
- Values use the same format: `<language> phoneme ...` for a single syllable
- Overrides are **global**: a syllable like "ling" is replaced wherever it appears in any word
- Ignored for words that already have a `word_prefs` match

Use this when a particular syllable consistently translates poorly and you've found a better alternative. This is especially useful for syllables that appear across many words.

### Precedence Rules

1. **word_prefs** is checked first. If a word matches, its entire output is replaced and `syl_prefs` is not consulted for that word.
2. **syl_prefs** is checked for each syllable of words that have no `word_prefs` match.
3. Syllables with no preference match use the automatic translation as before.

### Section 5: phoneme_map

**Purpose**: Maps each IPA phoneme to possible SynthV equivalents

```json
"phoneme_map": {
  "b": [
    {"lang": "spanish", "ph": "b"},
    {"lang": "english", "ph": "b"},
    {"lang": "japanese", "ph": "b"}
  ],
  "ɔ": [
    {"lang": "english", "ph": "ao", "weight": 2.0},
    {"lang": "spanish", "ph": "o"}
  ]
}
```

#### Entry Structure

For each IPA phoneme, provide an array of alternatives:

```json
"ipa_symbol": [
  {"lang": "language_name", "ph": "synthv_symbol", "weight": optional_weight}
]
```

- **lang**: SynthV voice language
  - Options: `english`, `spanish`, `japanese`, `mandarin`, `cantonese`, `korean`
- **ph**: The phoneme symbol in that language's notation
  - English: ARPABET (aa, eh, ih, etc.)
  - Spanish: X-SAMPA (a, e, i, o, u, etc.)
  - Japanese: Romaji (a, i, u, e, o, etc.)
  - Chinese: X-SAMPA variants
- **weight**: (optional) Preference score (higher = more preferred)

#### Ordering of Alternatives

The order matters for two reasons:
1. **Position-based weighting**: Earlier entries get higher base weight
2. **Fallback sequence**: If single-language fails, tries alternatives in order

**Best practice:**
1. Most accurate phonetic match first
2. Close approximations next
3. Acceptable fallbacks last

## IPA to SynthV Conversion

### Finding IPA Symbols

Test what IPA symbols eSpeak produces for your language:

```bash
echo "test word" | espeak-ng -v de --ipa
```

**Example outputs:**
- German "Hallo": `haloː`
- French "Bonjour": `bɔ̃ʒuːʁ`
- Italian "Ciao": `tʃaʊ`

### SynthV Phoneme Inventories

For a complete reference of available phonemes in each language, generate the phoneme inventory from your local Synthesizer V installation:

```bash
python generate_phoneme_inventory.py
```

This creates `mappings/sv_phoneme_inventory.json` with all available SynthV phonemes organized by language. The file is for local development use only and should not be committed to the repository.

Below are the most commonly used phonemes for reference:

#### English (ARPABET)

**Vowels:**
- `aa` - "father" [ɑ]
- `ae` - "cat" [æ]
- `eh` - "bed" [ɛ]
- `ih` - "bit" [ɪ]
- `iy` - "beat" [i]
- `uh` - "book" [ʊ]
- `uw` - "boot" [u]
- `ax` - "about" [ə]

**Diphthongs:**
- `ay` - "bite" [aɪ]
- `aw` - "bout" [aʊ]
- `oy` - "boy" [ɔɪ]
- `ey` - "bait" [eɪ]
- `ow` - "boat" [oʊ]

**Consonants:**
- Stops: `b d g k p t`
- Fricatives: `f v s z sh zh th dh hh`
- Affricates: `ch jh`
- Nasals: `m n ng`
- Liquids: `l r`
- Glides: `w y`

#### Spanish (X-SAMPA)

**Vowels:** `a e i o u`

**Consonants:**
- Stops: `b d g k p t`
- Fricatives: `f s x` (x = [x] as in "jota")
- Affricates: `ch` [tʃ]
- Nasals: `m n N J`
- Liquids: `l r rr` (rr = trilled r)
- Glides: `y` [j]

#### Japanese (Romaji)

**Vowels:** `a i u e o N` (N = ん)

**Consonants:**
- Stops: `k g t d b p`
- Affricates: `ts ch j z`
- Fricatives: `s sh f h`
- Nasals: `m n ny`
- Liquids: `r ry`
- Glides: `w y`

### Mapping Strategy

#### 1. Exact Matches

When IPA and SynthV have the same phoneme:

```json
"a": [{"lang": "spanish", "ph": "a"}]
```

#### 2. Close Approximations

When no exact match exists, find the closest:

```json
"ɛ": [
  {"lang": "english", "ph": "eh"},
  {"lang": "spanish", "ph": "e"}
]
```

IPA [ɛ] (open-mid front) → English "eh" is closer than Spanish "e"

#### 3. Multi-Phoneme Mappings

Some IPA phonemes may need multiple SynthV phonemes:

```json
"pf": [
  {"lang": "spanish", "ph": "p f", "weight": 2.0},
  {"lang": "english", "ph": "p f"}
]
```

German [pf] → "p f" sequence

#### 4. Diphthongs

```json
"aɪ": [
  {"lang": "english", "ph": "ay"},
  {"lang": "spanish", "ph": "a i"}
]
```

English has dedicated diphthong "ay", Spanish uses sequence "a i"

## Weighting System

### How Weights Work

Each alternative gets a score:

```
total_weight = position_weight + custom_weight
```

- **position_weight**: Automatically assigned based on list position
  - Earlier in list = higher weight
  - Calculated: `(max_options - position)`
- **custom_weight**: Optional "weight" field in mapping
  - Default: 0.0 if not specified

### Example Calculation

```json
"l": [
  {"lang": "spanish", "ph": "l", "weight": 2.0},
  {"lang": "english", "ph": "l"}
]
```

If max_options across all phonemes = 4:
- Spanish "l": position_weight = 4, custom_weight = 2.0 → total = 6.0
- English "l": position_weight = 3, custom_weight = 0.0 → total = 3.0

Spanish "l" is strongly preferred.

### When to Use Weights

**Use weights to:**
- **Prioritize better matches**: Higher weight for more accurate phonemes
- **Prefer certain languages**: Boost alternatives that sound more natural
- **Override position**: Make later alternatives preferred if needed

**Example use case:**
```json
"tʃ": [
  {"lang": "english", "ph": "ch", "weight": 2.0},
  {"lang": "spanish", "ph": "ch"},
  {"lang": "japanese", "ph": "ch"}
]
```

English "ch" works best for [tʃ], weight boosts it significantly.

## Creating a New Mapping

### Step-by-Step Process

#### 1. Research the Language

- Find phoneme inventory
- Check eSpeak output: `echo "text" | espeak-ng -v [lang] --ipa`
- List all IPA symbols eSpeak produces

#### 2. Start with Template

```json
{
  "vowels_orth": "",
  "ipa_process": [],
  "word_prefs": {},
  "syl_prefs": {},
  "phoneme_map": {}
}
```

#### 3. Fill in vowels_orth

List all orthographic vowels:
```json
"vowels_orth": "aeiouáéíóú"
```

#### 4. Map Common Phonemes First

Start with simple, common phonemes:

**Stops:**
```json
"p": [{"lang": "spanish", "ph": "p"}],
"t": [{"lang": "spanish", "ph": "t"}],
"k": [{"lang": "spanish", "ph": "k"}],
"b": [{"lang": "spanish", "ph": "b"}],
"d": [{"lang": "spanish", "ph": "d"}],
"g": [{"lang": "spanish", "ph": "g"}]
```

**Nasals:**
```json
"m": [{"lang": "spanish", "ph": "m"}],
"n": [{"lang": "spanish", "ph": "n"}]
```

#### 5. Map Vowels

```json
"a": [{"lang": "spanish", "ph": "a"}],
"e": [{"lang": "spanish", "ph": "e"}],
"i": [{"lang": "spanish", "ph": "i"}],
"o": [{"lang": "spanish", "ph": "o"}],
"u": [{"lang": "spanish", "ph": "u"}]
```

#### 6. Handle Special Phonemes

Map language-specific or complex phonemes:

```json
"x": [
  {"lang": "spanish", "ph": "x", "weight": 2.0},
  {"lang": "english", "ph": "hh"}
],
"ʎ": [
  {"lang": "spanish", "ph": "ll"},
  {"lang": "spanish", "ph": "y"}
]
```

#### 7. Add Alternatives

For each phoneme, add fallback alternatives from other languages:

```json
"s": [
  {"lang": "spanish", "ph": "s"},
  {"lang": "english", "ph": "s"},
  {"lang": "japanese", "ph": "s"}
]
```

#### 8. Test and Iterate

```bash
python synthv_translator.py -l [lang] -m your_mapping.json "test text"
```

Refine based on results.

## Testing and Refinement

### Test Suite

Create test cases covering:

1. **Simple words**: Single syllables
2. **Complex words**: Multiple syllables, clusters
3. **Common phrases**: Real-world usage
4. **Edge cases**: Unusual phoneme combinations

### Example Test File

`test/es_test.txt`:
```
hola
gracias
buenos días
trabajar
```

### Evaluation Criteria

- **Completeness**: All IPA symbols are mapped
- **Accuracy**: Phonemes sound close to original
- **Naturalness**: Language switching is minimal
- **Consistency**: Similar sounds map similarly

### Common Issues

**Issue 1: Unmapped phonemes**
```
Warning: The IPA sequence 'xyz' cannot be mapped
```

**Solution**: Add missing phoneme to `phoneme_map`

**Issue 2: Too many language switches**
```
<spanish> a - <english> b - <japanese> c
```

**Solution**: Add more alternatives, adjust weights

**Issue 3: Wrong syllabification**

**Solution**: Adjust `vowels_orth`, check pyphen dictionaries

## Reference Tables

### Common IPA → SynthV Mappings

| IPA | Sound | English | Spanish | Japanese |
|-----|-------|---------|---------|----------|
| a | "father" | aa | a | a |
| e | "bed" | eh | e | e |
| i | "beat" | iy, ih | i | i |
| o | "boat" | ow, ao | o | o |
| u | "boot" | uw | u | u |
| p | "pen" | p | p | p |
| t | "ten" | t | t | t |
| k | "cat" | k | k | k |
| b | "bed" | b | b | b |
| d | "dog" | d | d | d |
| g | "go" | g | g | g |
| m | "man" | m | m | m |
| n | "no" | n | n | n |
| l | "love" | l | l | - |
| r | "red" | r | r | r |
| s | "sun" | s | s | s |
| ʃ | "ship" | sh | sh | sh |
| tʃ | "church" | ch | ch | ch |

### IPA Consonant Chart

```
         Bilabial  Dental  Alveolar  Postalv  Palatal  Velar  Glottal
Plosive    p b              t d                         k g    ʔ
Nasal      m                n                           ŋ
Trill                       r
Tap                         ɾ
Fricative  f v      θ ð     s z       ʃ ʒ      ç        x      h
Approx.                     l                  j        w
```

### IPA Vowel Chart

```
         Front    Central   Back
Close    i y               u
Near-cl  ɪ ʏ               ʊ
Close-md e ø               o
Mid              ə
Open-md  ɛ œ               ɔ
Near-op  æ                 ɐ
Open     a                 ɑ ɒ
```

## Advanced Topics

### Multi-character IPA Sequences

Some IPA uses combinations:
```json
"aɪ̯": [{"lang": "english", "ph": "ay"}],
"tʃ": [{"lang": "english", "ph": "ch"}]
```

The tool segments using longest-match-first strategy.

### Handling Suprasegmentals

- **Length marks** (ː): Usually removed in `ipa_process`
- **Stress marks** (ˈ ˌ): Removed by phonemizer settings
- **Tone marks**: May need special handling for tonal languages

### Language-Specific IPA Process Rules

**German - R-vocalization:**
```json
["([aeiouäöü])r$", "\\1ɐ"]
```

**French - Nasal vowels:**
```json
["ã", "a~"],
["ɛ̃", "e~"]
```

**Polish - Palatalization:**
```json
["ɕ", "sh"],
["ʑ", "zh"]
```

## Resources

- **IPA Chart**: [https://www.internationalphoneticassociation.org/content/ipa-chart](https://www.internationalphoneticassociation.org/content/ipa-chart)
- **eSpeak NG Phonemes**: [https://github.com/espeak-ng/espeak-ng/blob/master/docs/phonemes.md](https://github.com/espeak-ng/espeak-ng/blob/master/docs/phonemes.md)
- **Synthesizer V Resources**: [https://dreamtonics.com/svstudio-resources/](https://dreamtonics.com/svstudio-resources/)
- **Reference mappings**: See existing files in `mappings/` directory

## Need Help?

- Open an issue on GitHub
- Check existing mapping files for examples
- Consult the IPA charts and phoneme inventories
- Test incrementally and iterate

---

Happy mapping!
