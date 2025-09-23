import re
import json
import pyphen

class PhonologicalSyllabifier:
    def __init__(self, rules_file: str = "mappings/de_syllable_rules.json"):
        with open(rules_file, encoding="utf-8") as f:
            self.rules = json.load(f)

        # Load phoneme classes
        self.vowels = set(self.rules.get("vowels", []))
        self.vowels_orth = set(self.rules.get("vowels_orth", []))
        self.diphthongs = set(self.rules.get("diphthongs", []))
        self.affricates = set(self.rules.get("affricates", []))
        self.allowed_onsets = set(self.rules.get("allowed_onsets", []))

        # Build phoneme→class map
        self.phoneme_to_class = {}
        for cls, phonemes in self.rules.items():
            if cls in ["vowels", "diphthongs", "affricates", "sonority_hierarchy", "allowed_onsets"]:
                continue
            for p in phonemes:
                self.phoneme_to_class[p] = cls
        for v in self.vowels:
            self.phoneme_to_class[v] = "vowel"
        for d in self.diphthongs:
            self.phoneme_to_class[d] = "diphthong"
        for a in self.affricates:
            self.phoneme_to_class[a] = "affricate"

        self.sonority = self.rules["sonority_hierarchy"]


    def _tokenize(self, ipa: str):
        """Split IPA string into tokens, handling diphthongs & affricates."""
        specials = sorted(
            list(self.diphthongs | self.affricates | self.vowels),
            key=len,
            reverse=True
        )
        tokens, i = [], 0
        while i < len(ipa):
            matched = False
            for sp in specials:
                if ipa.startswith(sp, i):
                    tokens.append(sp)
                    i += len(sp)
                    matched = True
                    break
            if not matched:
                tokens.append(ipa[i])
                i += 1
        return tokens


    def _classify(self, phoneme: str):
        return self.phoneme_to_class.get(phoneme, "stop")


    def _sonority(self, phoneme: str):
        return self.sonority.get(self._classify(phoneme), 0)


    def syllabify_text_orthographically(self, text: str, lang: str) -> list[list[str]]:
        # syllabify words
        dic = pyphen.Pyphen(lang=lang)
        words = text.strip().split()
        syllabified_words = [dic.inserted(word) for word in words]

        # post-processing
        vowel_e_re = re.compile(rf"[{re.escape(''.join(self.vowels_orth))}][eE]$")
        vowel_hb_re = re.compile(rf"[{re.escape(''.join(self.vowels_orth))}][hb]$")
        for idx, word in enumerate(syllabified_words):
            syls = word.split("-")
            # add unrecognized syllables
            if len(syls) == 1:
                if vowel_hb_re.search(syls[0][:2].lower()):
                    syls = [syls[0][0], syls[0][1:]]
                elif vowel_e_re.search(syls[0][-2:].lower()):
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
                if not any([v in syls[i].lower() for v in self.vowels_orth]):
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
        return syllabified_words


    def syllabify_ipa_phonologically(self, ipa: str):
        tokens = self._tokenize(ipa)
        nuclei = [i for i, t in enumerate(tokens) if self._classify(t) in ("vowel", "diphthong")]
        if not nuclei:
            return [ipa]

        syllables, last_boundary = [], 0

        for ni, nuc_idx in enumerate(nuclei):
            if ni == 0:
                continue
            prev_nuc = nuclei[ni - 1]
            curr_nuc = nuc_idx
            cluster = tokens[prev_nuc + 1:curr_nuc]
            if not cluster:
                continue

            split = prev_nuc + 1
            # Try maximal onset with legality check
            for k in range(len(cluster)):
                onset = cluster[k:]
                if self._is_valid_onset(onset):
                    split = prev_nuc + 1 + k
                    break

            syllables.append("".join(tokens[last_boundary:split]))
            last_boundary = split

        syllables.append("".join(tokens[last_boundary:]))
        return syllables


    def _is_valid_onset(self, onset_tokens):
        if not onset_tokens:
            return True
        onset_str = "".join(onset_tokens)
        if onset_str in self.allowed_onsets:
            return True
        sonorities = [self._sonority(p) for p in onset_tokens]
        return sonorities == sorted(sonorities)
