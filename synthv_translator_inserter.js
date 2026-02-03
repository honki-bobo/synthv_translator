// SynthV Translator Inserter
// Takes the output of synthv_translator.py and applies phonemes + language
// overrides to selected notes in the piano roll.
// When a syllable has intra-syllable language switches, the note is split
// into multiple notes at phoneme boundaries.

function getClientInfo() {
  return {
    name: "SynthV Translator Inserter",
    category: "Phoneme",
    author: "Martin Blankenburg",
    versionNumber: 1,
    minEditorVersion: 65540
  };
}

// ---------------------------------------------------------------------------
// Vowel table: paste the output of generate_phoneme_inventory.py --js here.
// This table maps each language to its vowel and diphthong phonemes, used to
// give vowels more weight when splitting notes across language groups.
// If absent, all phonemes are weighted equally.



// ---------------------------------------------------------------------------

/**
 * Calculate the weight of a phoneme group's phonemes.
 * Vowels/diphthongs get weight 2, all other phonemes get weight 1.
 * Falls back to equal weight (1 per phoneme) if VOWELS is not defined.
 */
function getGroupWeight(group) {
  var phonemeList = group.phonemes.split(/\s+/);
  if (typeof VOWELS === "undefined") {
    return phonemeList.length;
  }
  var langVowels = VOWELS[group.lang];
  if (!langVowels) {
    return phonemeList.length;
  }
  var weight = 0;
  for (var i = 0; i < phonemeList.length; i++) {
    weight += langVowels[phonemeList[i]] ? 2 : 1;
  }
  return weight;
}

/**
 * Strip brackets and take the first alternative before " | ".
 */
function resolveAlternatives(s) {
  s = s.trim();
  if (s.charAt(0) === "[" && s.charAt(s.length - 1) === "]") {
    s = s.substring(1, s.length - 1);
  }
  var pipeIdx = s.indexOf(" | ");
  if (pipeIdx !== -1) {
    s = s.substring(0, pipeIdx);
  }
  return s.trim();
}

/**
 * Parse the output of synthv_translator.py into a flat array of syllable
 * objects. Each syllable has a `groups` array of {lang, phonemes} entries
 * representing consecutive phonemes in the same language.
 *
 * Input example (output of: synthv_translator.py "Guten Morgen Deutschland"):
 *   "<spanish> g u - t e n\n<spanish> m o r - g e n\n<english> d ao ey uw ch - <spanish> l a n t"
 *
 * Returns:
 *   [{groups:[{lang:"spanish", phonemes:"g u"}]},
 *    {groups:[{lang:"spanish", phonemes:"t e n"}]},
 *    {groups:[{lang:"spanish", phonemes:"m o r"}]},
 *    {groups:[{lang:"spanish", phonemes:"g e n"}]},
 *    {groups:[{lang:"english", phonemes:"d ao ey uw ch"}]},
 *    {groups:[{lang:"spanish", phonemes:"l a n t"}]}]
 */
function parseInput(text) {
  var syllables = [];
  var currentLang = "english"; // default fallback

  var lines = text.split("\n");
  for (var li = 0; li < lines.length; li++) {
    var line = lines[li].trim();
    if (line === "") continue;

    // Split line into syllable segments by " - "
    var segments = line.split(" - ");
    for (var si = 0; si < segments.length; si++) {
      var segment = resolveAlternatives(segments[si]);
      if (segment === "") continue;

      var tokens = segment.split(/\s+/);
      var groups = [];
      var langForGroup = null;
      var phonemeBuf = [];

      for (var ti = 0; ti < tokens.length; ti++) {
        var tok = tokens[ti];
        // Check for language tag like <english>, <spanish>, etc.
        var langMatch = tok.match(/^<(\w+)>$/);
        if (langMatch) {
          // Flush accumulated phonemes before switching language
          if (phonemeBuf.length > 0) {
            groups.push({
              lang: langForGroup || currentLang,
              phonemes: phonemeBuf.join(" ")
            });
            phonemeBuf = [];
          }
          langForGroup = langMatch[1];
          currentLang = langForGroup;
        } else {
          // If no language tag seen yet for this segment, inherit
          if (langForGroup === null) {
            langForGroup = currentLang;
          }
          phonemeBuf.push(tok);
        }
      }

      // Flush remaining phonemes
      if (phonemeBuf.length > 0) {
        groups.push({
          lang: langForGroup || currentLang,
          phonemes: phonemeBuf.join(" ")
        });
      }

      if (groups.length > 0) {
        syllables.push({ groups: groups });
        // Track the last language used for inheritance
        currentLang = groups[groups.length - 1].lang;
      }
    }
  }

  return syllables;
}

/**
 * Check whether a note's lyrics indicate it should be skipped (no syllable consumed).
 * Skipped: "-" (melisma), "br" (breath), "'" (standalone glottal stop).
 */
function isSkippedNote(lyrics) {
  return lyrics === "-" || lyrics === "br" || lyrics === "'";
}

/**
 * Count how many of the selected notes consume a syllable.
 * Skipped notes ("-", "br", "'") do not consume syllables.
 */
function countSyllableNotes(notes) {
  var count = 0;
  for (var i = 0; i < notes.length; i++) {
    if (!isSkippedNote(notes[i].getLyrics())) {
      count++;
    }
  }
  return count;
}

/**
 * Split a note into multiple sub-notes when a syllable has multiple language
 * groups. Duration is distributed proportionally to each group's phoneme
 * weight (vowels count more than consonants). The first group reuses the
 * original note; subsequent groups create new "-" (melisma) notes.
 */
function splitNoteForGroups(note, groups, noteGroup) {
  var onset = note.getOnset();
  var duration = note.getDuration();
  var pitch = note.getPitch();

  // Calculate weights for proportional duration splitting
  var weights = [];
  var totalWeight = 0;
  for (var i = 0; i < groups.length; i++) {
    var w = getGroupWeight(groups[i]);
    weights.push(w);
    totalWeight += w;
  }

  // Calculate durations and onsets from weights
  var durations = [];
  var usedDuration = 0;
  for (var i = 0; i < groups.length; i++) {
    if (i === groups.length - 1) {
      // Last group gets remaining duration to avoid rounding gaps
      durations.push(duration - usedDuration);
    } else {
      var d = Math.floor(duration * weights[i] / totalWeight);
      durations.push(d);
      usedDuration += d;
    }
  }

  // First group: modify the original note in place
  note.setDuration(durations[0]);
  note.setLanguageOverride(groups[0].lang);
  note.setPhonemes(groups[0].phonemes);

  // Remaining groups: create new notes
  var currentOnset = onset + durations[0];
  for (var i = 1; i < groups.length; i++) {
    var newNote = SV.create("Note");
    newNote.setOnset(currentOnset);
    newNote.setDuration(durations[i]);
    newNote.setPitch(pitch);
    newNote.setLyrics("-");
    newNote.setLanguageOverride(groups[i].lang);
    newNote.setPhonemes(groups[i].phonemes);
    noteGroup.addNote(newNote);
    currentOnset += durations[i];
  }
}

/**
 * Main entry point. Shows a dialog for pasting translator output, parses it,
 * then walks through selected notes applying phonemes and language overrides.
 */
function main() {
  var editor = SV.getMainEditor();
  var selection = editor.getSelection();
  var selectedNotes = selection.getSelectedNotes();

  if (selectedNotes.length === 0) {
    SV.showMessageBox("SynthV Translator Inserter", "No notes selected. Please select notes in the piano roll first.");
    SV.finish();
    return;
  }

  // Sort selected notes by onset time so we process them in order
  selectedNotes.sort(function(a, b) {
    return a.getOnset() - b.getOnset();
  });

  // Show input dialog
  var dialog = {
    title: "SynthV Translator Inserter",
    message: "Paste the output of synthv_translator.py below.\nEach line = one word, syllables separated by \" - \".",
    buttons: "OkCancel",
    widgets: [
      {
        name: "phonemeInput",
        type: "TextArea",
        label: "SynthV Translator Output",
        height: 200,
        default: ""
      }
    ]
  };

  var result = SV.showCustomDialog(dialog);

  if (result.status !== true) {
    // Dialog cancelled
    SV.finish();
    return;
  }

  var inputText = result.answers.phonemeInput;
  if (!inputText || inputText.trim() === "") {
    SV.showMessageBox("SynthV Translator Inserter", "No input provided. Please paste the translator output.");
    SV.finish();
    return;
  }

  var syllables = parseInput(inputText.trim());

  if (syllables.length === 0) {
    SV.showMessageBox("SynthV Translator Inserter", "Could not parse any syllables from the input.");
    SV.finish();
    return;
  }

  // Count how many notes will consume syllables
  var syllableNoteCount = countSyllableNotes(selectedNotes);

  if (syllableNoteCount > syllables.length) {
    SV.showMessageBox("SynthV Translator Inserter",
      "Not enough syllables for the selected notes.\n" +
      "Notes that need syllables: " + syllableNoteCount + "\n" +
      "Syllables parsed: " + syllables.length);
    SV.finish();
    return;
  }

  // Get the NoteGroup that the selected notes belong to
  var noteGroup = editor.getCurrentGroup().getTarget();

  // Walk through notes and apply syllables
  var sylIdx = 0;
  var lastLang = null;
  var applied = 0;

  for (var ni = 0; ni < selectedNotes.length; ni++) {
    var note = selectedNotes[ni];
    var lyrics = note.getLyrics();

    if (isSkippedNote(lyrics)) {
      // Melisma "-", breath "br", or glottal stop "'": don't consume syllable
      if (lastLang !== null && lyrics !== "br") {
        note.setLanguageOverride(lastLang);
      }
    } else {
      // Regular note or "+": consume next syllable
      if (sylIdx >= syllables.length) {
        // Should not happen due to earlier check, but guard anyway
        break;
      }

      var syl = syllables[sylIdx];
      sylIdx++;

      if (syl.groups.length === 1) {
        // Single language group: set directly on the note
        note.setLanguageOverride(syl.groups[0].lang);
        note.setPhonemes(syl.groups[0].phonemes);
      } else {
        // Multiple language groups: split the note
        splitNoteForGroups(note, syl.groups, noteGroup);
      }

      lastLang = syl.groups[syl.groups.length - 1].lang;
      applied++;
    }
  }

  // Report result
  var msg = "Applied " + applied + " syllable(s) to notes.";
  if (sylIdx < syllables.length) {
    msg += "\nWarning: " + (syllables.length - sylIdx) + " extra syllable(s) were not used.";
  }
  SV.showMessageBox("SynthV Translator Inserter", msg);
  SV.finish();
}
