# Synthesizer V Translator

A powerful command-line tool that translates text from various languages into phoneme sequences compatible with [Synthesizer V](https://dreamtonics.com/synthesizerv/) by Dreamtonics. This tool enables you to make Synthesizer V voices sing in languages they weren't originally designed for by leveraging eSpeak's extensive language support.

## Features

- **Multi-language Support**: Translate text from German, French, Italian, Portuguese, and Russian (any language supported by eSpeak NG)
- **Intelligent Syllabification**: Automatic syllable boundary detection using orthographic and phonological rules
- **Phoneme Mapping**: Converts IPA phonemes to Synthesizer V's multi-language phoneme format
- **Alternative Pronunciations**: Generate multiple pronunciation alternatives with weighted ranking
- **Language Switching Optimization**: Minimizes language switches within syllables for more natural results
- **Flexible Output**: Support for single or multiple alternative phoneme sequences

## How It Works

1. **Text Input**: Takes text in the source language (e.g., German, French)
2. **Syllabification**: Splits words into syllables using pyphen
3. **IPA Conversion**: Converts syllables to International Phonetic Alphabet (IPA) using eSpeak NG
4. **Phoneme Alignment**: Aligns syllable boundaries with correct phonology
5. **SynthV Mapping**: Maps IPA phonemes to Synthesizer V phonemes across available voice languages
6. **Output**: Generates formatted phoneme sequences ready for Synthesizer V

## Installation

### Prerequisites

- **Python 3.11 or higher**
- **eSpeak NG** (text-to-speech engine)

### Step 1: Install eSpeak NG

**Windows:**
1. Download the eSpeak NG installer (`espeak-ng.msi`) from [GitHub Releases](https://github.com/espeak-ng/espeak-ng/releases)
2. Run the installer
3. Open PowerShell as **Administrator** and set environment variables:
   ```powershell
   setx PHONEMIZER_ESPEAK_PATH "C:\Program Files\eSpeak NG\espeak-ng.exe"
   setx PHONEMIZER_ESPEAK_LIBRARY "C:\Program Files\eSpeak NG\libespeak-ng.dll"
   ```
4. Close and reopen PowerShell for changes to take effect

**Linux:**
```bash
sudo apt-get install espeak-ng
```

**macOS:**
```bash
brew install espeak-ng
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install phonemizer pyphen
```

### Step 3: Clone the Repository

```bash
git clone https://github.com/honki-bobo/synthv_translator.git
cd synthv_translator
```

## Usage

### Basic Usage

Translate text directly from command line:

```bash
python synthv_translator.py Dies ist ein Text in deutscher Sprache
```

**Output:**
```
<spanish> d i s
<spanish> i s t
<english> ay n
<spanish> t e k s t
<english> ih n
<spanish> d o e u t - <english> sh er
<english> sh p r aa - <spanish> x e
```

### Advanced Usage

**Specify language:**
```bash
python synthv_translator.py -l fr "Bonjour le monde"
```

**Use a custom mapping file:**
```bash
python synthv_translator.py -l fr -m my_custom_fr.json "Bonjour"
```

**Read from file:**
```bash
python synthv_translator.py -i input.txt -o output.txt
```

**Show alternative pronunciations:**
```bash
# Show top 3 alternatives per syllable
python synthv_translator.py -a 2 "Hallo Welt"

# Show all alternatives
python synthv_translator.py -a -1 "Hallo Welt"
```

**Enable phoneme-level language switching:**
```bash
python synthv_translator.py -p "komplexer Text"
```

### Command-Line Options

```
usage: synthv_translator.py [-h] [-i INPUT] [-l {de,fr,it,pt,ru}]
                            [-m MAP_FILE] [-a ALTERNATIVES] [-p]
                            [-o OUTPUT] [words ...]

Text → Synthesizer V phoneme translator

positional arguments:
  words                 Words to translate (ignored if -i is used)

optional arguments:
  -h, --help            Show this help message and exit
  -i INPUT, --input INPUT
                        Input text file (optional, defaults to stdin)
  -l {de,fr,it,pt,ru}, --lang {de,fr,it,pt,ru}
                        Language for phonemization (default: de)
  -m MAP_FILE, --map-file MAP_FILE
                        Path to the JSON mapping file (default: auto-detected from language)
  -a ALTERNATIVES, --alternatives ALTERNATIVES
                        Show N alternatives. -1 = all (default: 0)
  -p, --phoneme-edit    Allow language switching per phoneme instead of per syllable
  -o OUTPUT, --output OUTPUT
                        Output file (optional, defaults to stdout)
```

## Understanding the Output

The output format uses language tags followed by phonemes:

```
<spanish> d i s
```

- `<spanish>`: Language switch - following phonemes use Spanish voice
- `d i s`: Individual phonemes in SynthV format

**Syllable boundaries** are marked with hyphens (`-`):
```
<spanish> h a - l o
```

**Alternative pronunciations** are separated by pipes (`|`):
```
[<spanish> h a | <english> hh aa]
```

## Mapping Files

Mapping files define how IPA phonemes are converted to Synthesizer V phonemes. Each language has its own mapping file in the `mappings/` directory.

### Mapping File Structure

```json
{
  "vowels_orth": "aeiouyäöüÿ",
  "ipa_process": [
    ["([^aeiouyäöüɛɔœøɐəɜ])(ɾ|r)", "\\1ʁ"],
    ["^(ɾ|r)", "ʁ"]
  ],
  "phoneme_map": {
    "b": [
      {"lang": "spanish", "ph": "b"},
      {"lang": "english", "ph": "b"},
      {"lang": "japanese", "ph": "b"}
    ],
    "l": [
      {"lang": "spanish", "ph": "l", "weight": 2.0},
      {"lang": "english", "ph": "l"}
    ]
  }
}
```

- **vowels_orth**: Orthographic vowels for syllabification
- **ipa_process**: Regex patterns for IPA post-processing
- **phoneme_map**: Maps IPA phonemes to SynthV phonemes with optional weights

## Supported Languages

Currently supported input languages:
- German (de)
- French (fr)
- Italian (it)
- Portuguese (pt)
- Russian (ru)

Synthesizer V output languages:
- English (ARPABET)
- Spanish (X-SAMPA)
- Japanese (Romaji)
- Mandarin Chinese (X-SAMPA)
- Cantonese (X-SAMPA)
- Korean (X-SAMPA)

## Examples

### Example 1: German to SynthV
```bash
python synthv_translator.py -l de "Guten Morgen"
```

### Example 2: French with Alternatives
```bash
python synthv_translator.py -l fr -a 1 "Bonjour le monde"
```

### Example 3: Processing a File
```bash
python synthv_translator.py -l de -i lyrics.txt -o phonemes.txt
```

### Example 4: Russian Text
```bash
python synthv_translator.py -l ru "Привет мир"
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Adding New Languages

To add support for a new language:

1. Generate a phoneme reference (requires local SynthV installation):
   ```bash
   python generate_phoneme_inventory.py
   ```
2. Create a new mapping file in `mappings/` (e.g., `pl.json` for Polish)
3. Define `vowels_orth`, `ipa_process`, and `phoneme_map` (see [MAPPING_GUIDE.md](MAPPING_GUIDE.md))
4. Test with sample text
5. Add the language code to the argument parser in `synthv_translator.py`

**Note**: Spanish, English, Japanese, Mandarin, Cantonese, and Korean are already natively supported by Synthesizer V and don't require translation.

## License

This project is provided as-is for the Synthesizer V community. Please respect Dreamtonics' terms of service when using Synthesizer V.

## Acknowledgments

- **Dreamtonics** for creating Synthesizer V
- **eSpeak NG** for comprehensive phonemization support
- The open-source community for pyphen and phonemizer libraries

## Troubleshooting

**Issue: "Could not read file" error**
- Ensure the mapping file path is correct
- Check that the mapping file is valid JSON

**Issue: eSpeak not found**
- Verify eSpeak NG is installed
- Check environment variables are set correctly
- Restart your terminal/PowerShell

**Issue: Poor pronunciation quality**
- Try different alternatives with `-a` flag
- Adjust phoneme weights in the mapping file
- Use `-p` flag for more flexible language switching

## Contact

For issues, questions, or suggestions, please open an issue on GitHub.

---

**Note**: This is an unofficial tool created by the community and is not affiliated with Dreamtonics.
