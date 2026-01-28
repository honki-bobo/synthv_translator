# Contributing to Synthesizer V Translator

Thank you for your interest in contributing to Synthesizer V Translator! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Creating Language Mappings](#creating-language-mappings)
- [Testing Your Changes](#testing-your-changes)
- [Submitting Changes](#submitting-changes)

## Code of Conduct

This project aims to be welcoming and inclusive. Please be respectful and constructive in all interactions.

## How Can I Contribute?

### Reporting Bugs

If you find a bug, please open an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, eSpeak version)
- Sample input text that demonstrates the issue

### Suggesting Enhancements

Enhancement suggestions are welcome! Please open an issue describing:
- The enhancement you'd like to see
- Why it would be useful
- Possible implementation approaches (if you have ideas)

### Adding Support for New Languages

One of the most valuable contributions is adding support for new languages. See [Creating Language Mappings](#creating-language-mappings) below.

### Improving Documentation

Documentation improvements are always appreciated:
- Fixing typos or clarifying instructions
- Adding examples
- Translating documentation
- Improving code comments

### Code Contributions

- Bug fixes
- Performance improvements
- New features
- Test coverage improvements

## Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/honki-bobo/synthv_translator.git
   cd synthv_translator
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify your setup**
   ```bash
   python synthv_translator.py -l de "Test"
   ```

5. **Generate phoneme inventory reference** (optional, for creating new language mappings)

   If you plan to create new language mappings, you'll need a reference of available SynthV phonemes. This requires a local Synthesizer V installation:

   ```bash
   python generate_phoneme_inventory.py
   ```

   Or specify a custom path to your SynthV installation:
   ```bash
   python generate_phoneme_inventory.py "C:\Path\To\Synthesizer V Studio\clf-data"
   ```

   This generates `mappings/sv_phoneme_inventory.json` for your local use. **Note**: This file is gitignored and should not be committed or redistributed due to licensing restrictions.

## Creating Language Mappings

Adding a new language involves creating a mapping file that defines how IPA phonemes from that language map to Synthesizer V phonemes.

### Step 1: Understand the Language's Phonology

1. Research the language's phoneme inventory
2. Find the IPA symbols used by eSpeak NG for that language
3. Test eSpeak output for your language:
   ```bash
   echo "test text" | espeak-ng -v [language-code] --ipa
   ```

### Step 2: Create the Mapping File

Create a new JSON file in the `mappings/` directory (e.g., `mappings/pl.json` for Polish):

**Note**: Spanish, English, Japanese, Mandarin, Cantonese, and Korean are already natively supported by Synthesizer V and don't require translation mappings.

```json
{
  "vowels_orth": "aeiouáéíóú",
  "ipa_process": [],
  "phoneme_map": {
    "a": [
      {"lang": "spanish", "ph": "a"},
      {"lang": "english", "ph": "aa"}
    ]
  }
}
```

#### Field Descriptions

**`vowels_orth`**: String containing all orthographic vowels in the language (used for syllabification)

**`ipa_process`**: Array of regex replacement patterns to post-process IPA output from eSpeak
```json
"ipa_process": [
  ["pattern_to_match", "replacement"],
  ["([^vowels])(r)", "\\1ʁ"]
]
```

**`phoneme_map`**: Object mapping IPA phonemes to Synthesizer V phonemes

Each IPA phoneme maps to an array of possible SynthV representations:
```json
"ɔ": [
  {"lang": "english", "ph": "ao", "weight": 2.0},
  {"lang": "spanish", "ph": "o"}
]
```

- `lang`: SynthV voice language (english, spanish, japanese, mandarin, cantonese, korean)
- `ph`: The phoneme symbol in that language's notation
- `weight`: (optional) Preference weight for this mapping (higher = preferred)

#### Mapping Strategy

1. **Start with common phonemes**: Map consonants and basic vowels first
2. **Check phoneme inventories**: Use `mappings/sv_phoneme_inventory.json` to see available SynthV phonemes (generate it first using `python generate_phoneme_inventory.py`)
3. **Prioritize close matches**: List the closest phonetic match first
4. **Add alternatives**: Include fallback options from other languages
5. **Test iteratively**: Test with sample text and refine mappings

### Step 3: Reference Files

Use these reference files in the `mappings/` directory:

- `sv_phoneme_inventory.json`: Complete list of available SynthV phonemes per language
- Existing language mappings (`de.json`, `fr.json`, etc.): Examples to follow

### Step 4: Add Language to Code

Edit `synthv_translator.py` to add your language to the choices:

```python
parser.add_argument(
    "-l",
    "--lang",
    type=str,
    choices=["de", "fr", "it", "pt", "ru", "pl"],  # Add your language code
    default="de",
    help="Language for phonemization (default: de)",
)
```

Update the default mapping path if needed:
```python
parser.add_argument(
    "-m",
    "--map-file",
    type=str,
    default="mappings\de.json",  # Users can override this
    help="Path to the JSON mapping file",
)
```

## Testing Your Changes

### Manual Testing

Test with a variety of input:

```bash
# Basic test
python synthv_translator.py -l pl -m mappings/pl.json "Cześć świat"

# Test with file input
echo "Longer test text" > test_input.txt
python synthv_translator.py -l pl -m mappings/pl.json -i test_input.txt

# Test alternatives
python synthv_translator.py -l pl -m mappings/pl.json -a 2 "test"
```

### Test Cases to Cover

1. **Single words**: Simple, common words
2. **Multi-syllable words**: Complex syllabification
3. **Special characters**: Accented characters, umlauts, etc.
4. **Edge cases**: Single letters, numbers, punctuation
5. **Common phrases**: Real-world usage examples

### Creating Test Files

Add test cases to the `test/` directory:
```
test/
  pl_phoneme_test.txt
  pl_regression_test.txt
```

## Submitting Changes

### Pull Request Process

1. **Create a branch** for your changes
   ```bash
   git checkout -b feature/add-polish-support
   ```

2. **Make your changes** and commit with clear messages
   ```bash
   git add mappings/pl.json
   git commit -m "Add Polish language mapping"
   ```

3. **Test thoroughly** before submitting

4. **Push to your fork**
   ```bash
   git push origin feature/add-polish-support
   ```

5. **Open a Pull Request** with:
   - Clear description of changes
   - Examples of input/output
   - Any issues or limitations
   - Test results

### Pull Request Guidelines

- **One feature per PR**: Keep PRs focused
- **Update documentation**: Update README if needed
- **Test examples**: Include test cases or examples
- **Clean code**: Follow existing code style
- **Descriptive commits**: Use clear commit messages

### Commit Message Format

```
Add Polish language mapping

- Created mappings/pl.json with IPA to SynthV phoneme mappings
- Added 'pl' to language choices in argument parser
- Tested with common Polish phrases
```

## Questions?

If you have questions about contributing:
- Open an issue with the "question" label
- Check existing issues for similar questions
- Review the main README.md for usage information

Thank you for contributing to Synthesizer V Translator!
