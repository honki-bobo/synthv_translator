# Synthesizer V Translator - Usage Examples

This document provides detailed examples of how to use the Synthesizer V Translator for various use cases.

## Table of Contents

- [Basic Translation](#basic-translation)
- [Working with Files](#working-with-files)
- [Alternative Pronunciations](#alternative-pronunciations)
- [Language-Specific Examples](#language-specific-examples)
- [Advanced Usage](#advanced-usage)
- [Integration Workflows](#integration-workflows)

## Basic Translation

### Simple German Text

```bash
python synthv_translator.py "Hallo Welt"
```

**Output:**
```
<english> hh aa - <spanish> l o
<english> v eh l t
```

### Using Language Flag

```bash
python synthv_translator.py -l fr "Bonjour"
```

**Output:**
```
Warning: The IPA sequence 'ʒuʁ' cannot be mapped into a single language.
<spanish> b o - <english> zh <spanish> u <english> r
```

### Multiple Words

```bash
python synthv_translator.py "Guten Morgen Deutschland"
```

**Output:**
```
<spanish> g u - t e n
<spanish> m o r - g e n
<english> d ao ey uw ch - <spanish> l a n t
```

## Working with Files

### Reading from a File

Create an input file `lyrics.txt`:
```
Stille Nacht
Heilige Nacht
Alles schläft
```

Run the translator:
```bash
python synthv_translator.py -i lyrics.txt
```

### Writing to a File

```bash
python synthv_translator.py -i lyrics.txt -o output.txt
```

This saves the phoneme output to `output.txt`.

### Using stdin/stdout (Unix-style pipes)

```bash
echo "Test Text" | python synthv_translator.py
```

Or:
```bash
cat input.txt | python synthv_translator.py > output.txt
```

## Alternative Pronunciations

### Show Top Alternative

```bash
python synthv_translator.py -a 1 "Hallo"
```

**Output:**
```
[<english> hh aa | <spanish> h a] - [<spanish> l o | <english> l ao]
```

The pipe `|` separates alternatives. The first option before the pipe is the primary suggestion.

### Show Multiple Alternatives

```bash
python synthv_translator.py -a 2 "Test"
```

Shows the top 3 alternatives (0, 1, 2) for each syllable.

### Show All Alternatives

```bash
python synthv_translator.py -a -1 "Hallo"
```

Displays every possible phoneme combination (can be very long for complex words).

## Language-Specific Examples

### German (de)

Doesn't need language switch, "de" is the default.

```bash
python synthv_translator.py "Schöne Grüße"
```

**Output:**
```
<english> sh ey uw - <spanish> n e
<spanish> g rr i u - s e
```

German umlauts (ä, ö, ü) and special characters are properly handled.

### French (fr)

```bash
python synthv_translator.py -l fr "Je t'aime"
```

**Output:**
```
<english> zh ax
<spanish> t e m
```

### Italian (it)

```bash
python synthv_translator.py -l it "Ciao bella"
```

**Output:**
```
<english> ch <spanish> a o
<spanish> b e l - l a
```

### Portuguese (pt)

```bash
python synthv_translator.py -l pt "Olá mundo"
```

**Output:**
```
<spanish> o l a
<spanish> m u <english> ng <spanish> d <english> uh
```

### Russian (ru)

```bash
python synthv_translator.py -l ru "Привет"
```

**Output:**
```
<spanish> p rr i - v e t
```

Russian Cyrillic characters are supported via eSpeak NG.

## Advanced Usage

### Phoneme-Level Language Switching

By default, the tool tries to keep each syllable in a single language. Use `-p` to allow language switching within a syllable:

```bash
python synthv_translator.py -p "komplexer"
```

**Without `-p`** (syllable-level):
```
<spanish> k o m - p l e - k s e
```

**With `-p`** (phoneme-level):
```
<spanish> k <english> ao <spanish> m - p l <english> eh - <spanish> k s <english> er
```

This gives more flexibility but may sound less natural.

### Custom Mapping Files

Create your own mapping file or modify an existing one:

```bash
python synthv_translator.py -l de -m my_custom_mapping.json "Test"
```

The mapping file is auto-detected based on the `-l` language flag (e.g., `-l fr` uses `mappings/fr.json`). Use `-m` only when you want to override this with a custom file.

This is useful for:
- Dialect-specific pronunciations
- Fine-tuning phoneme choices, i.e. for a specific SynthV voice
- Experimenting with alternative mappings

### Batch Processing

Process multiple files in a loop:

**Windows PowerShell:**
```powershell
Get-ChildItem *.txt | ForEach-Object {
    python synthv_translator.py -l de -i $_.Name -o "$($_.BaseName)_phonemes.txt"
}
```

**Linux/Mac:**
```bash
for file in *.txt; do
    python synthv_translator.py -l de -i "$file" -o "${file%.txt}_phonemes.txt"
done
```

## Integration Workflows

### Workflow 1: Song Lyrics Translation

1. **Prepare lyrics** in a text file:
   ```
   First line
   Second line

   Chorus line
   ```

2. **Translate**:
   ```bash
   python synthv_translator.py -i song_lyrics.txt -o phonemes.txt
   ```

3. **Review alternatives** for problem words:
   ```bash
   python synthv_translator.py -a 2 "problematic-word"
   ```

4. **Copy phonemes** to Synthesizer V's phoneme field

### Workflow 2: Testing Different Languages

Compare how a word sounds in different SynthV voice languages:

```bash
# German source, different mappings
python synthv_translator.py "Liebe"
python synthv_translator.py -a 2 "Liebe"  # See alternatives
```

Look at the language tags to see which voice would pronounce each syllable.

### Workflow 3: Building a Pronunciation Dictionary

Create a reference file of common words:

```bash
# Create word list
echo "Hallo
Tschüss
Danke
Bitte" > common_words.txt

# Generate phonemes
python synthv_translator.py -i common_words.txt -o pronunciation_dict.txt
```

Keep this as a reference for consistent pronunciation across projects.

## Practical Tips

### Tip 1: Handling Problematic Words

If a word doesn't translate well:

1. **Check alternatives**: Use `-a 1` or `-a 2` to see other options
2. **Try phoneme-level**: Use `-p` flag
3. **Break it down**: Translate syllables separately
4. **Manual adjustment**: Copy the closest match and modify in Synthesizer V

### Tip 2: Optimizing for Specific Voices

Different SynthV voices may pronounce phonemes slightly differently:

- For **English voices**: Prefer English phonemes where possible
- For **Spanish voices**: Spanish phonemes often sound clearer
- For **Japanese voices**: May need special handling of 'r' and 'l' sounds

### Tip 3: Dealing with Names and Foreign Words

For names or foreign words in the text:

Option 1: Use the name's original language in SynthV, e.g. "Shakespeare"

Option 2: Use alternatives to find acceptable approximation
```bash
python synthv_translator.py -a 2 "Shakespeare"
```

### Tip 4: Syllable Boundary Issues

If syllable boundaries are wrong:

1. Check the `vowels_orth` setting in the mapping file
2. The tool uses pyphen for syllabification - some words may need manual adjustment
3. Use hyphens in output as guides, but adjust in SynthV if needed

## Example Session

Here's a complete example session translating a German phrase:

```bash
# Start with basic translation
$ python synthv_translator.py "Gute Nacht"
<spanish> g u - t e
<spanish> n a x t

# Check alternatives for "Nacht"
$ python synthv_translator.py -a 1 "Nacht"
[<spanish> n a x t | <english> n aa hh t]

# Prefer the second alternative, note it down

# Process full lyrics file
$ python synthv_translator.py -i lullaby.txt -o lullaby_phonemes.txt

# Review output file
$ cat lullaby_phonemes.txt
<spanish> g u - t e
<spanish> n a x t
<spanish> sh l a f
<spanish> sh e u n
```

## Common Output Patterns

### Single Language Syllables (Ideal)

```
<spanish> h a - l o
```
Each syllable uses one language - most natural sounding.

### Mixed Language Syllables

```
<spanish> d o e u t - <english> sh l a n d
```
Syllable switches languages mid-word - sometimes unavoidable for complex phoneme combinations.

### Alternative Brackets

```
[<spanish> h a | <english> hh aa]
```
Shows multiple pronunciation options. Test both to see which sounds better.

## Troubleshooting Examples

### Problem: Output is empty

```bash
$ python synthv_translator.py ""
# No output
```

**Solution**: Ensure you provide input text.

### Problem: Encoding errors

```bash
$ python synthv_translator.py "café"
# Error with special characters
```

**Solution**: Ensure your terminal supports UTF-8:
```bash
# Windows PowerShell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Linux/Mac - usually default UTF-8
```

### Problem: Wrong language phonemes

```bash
$ python synthv_translator.py "Bonjour"
# Gets German pronunciation of French word
```

**Solution**: Use the correct language flag:
```bash
$ python synthv_translator.py -l fr "Bonjour"
```

## Additional Resources

- [README.md](README.md) - Main documentation
- [CONTRIBUTING.md](CONTRIBUTING.md) - How to add new languages
- `mappings/` directory - Phoneme mapping reference files
- [Synthesizer V Manual](https://dreamtonics.com/svstudio-resources/) - Official SynthV documentation

---

For more examples or to share your use cases, please open an issue or discussion on GitHub!
