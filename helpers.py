import os
from mido import MidiFile, MidiTrack, Message, MetaMessage
from music21 import converter, expressions, harmony, note, key, environment
from musicaiz.harmony import chords, ChordQualities
import re
import tkinter as tk
from tkinter import simpledialog, messagebox

ALLOWED_CHORD_QUALITIES = [
    'm', 'minor', 'min', '-', 
    'M', 'major', 'maj', 'Δ', 
    'A', 'augmented', 'aug', '+', 
    'dis', 'diminished', 'dis', '°', 
    'M7', 'major seventh', 'maj7', 'Δ7', 'Δ', 
    'm7', 'minor seventh', '-7', '7', 'dominant seventh', 
    'dim7', 'diminished seventh', 'dim7', '°', 
    'mb5', '-b5', 'm7b5', 'half-diminished seventh', '-7b5', 'ø', 
    'mM7', 'minor major seventh', 'm maj7', 'mΔ7', '-Δ7', 
    'maj7#5', 'augmented major seventh', '+M7', '+Δ7', 'aug7', 'augmented seventh', '+7', 
    'mM7b5', 'diminished major seventh', '−Δ7b5', '7b5', 'dominant seventh flat five', 'M7b5', 'major seventh flat five'
]

def update_track_in_midi_file(midi_file, bars_data, pitch_offset=60, velocity=60, channel=0):
    """
    Replaces the existing note_on/note_off events in Track 1 of a MidiFile 
    with new events derived from (pitch_class, duration_in_ticks) data.

    :param midi_file:   A mido.MidiFile object with at least two tracks 
                        (track 0 typically has tempo/time-signature, track 1 is music data).
    :param bars_data:   Nested list of (pitch_class, duration_in_ticks) entries.
                        Example:
                          [
                            [(2, 480), (0, 240), (9, 240), ...],
                            [(2, 240), (0, 240), (9, 240), (11, 240), ...],
                            ...
                          ]
    :param pitch_offset: MIDI note number for pitch_class=0. 
                        60 => middle C, 72 => C one octave higher, etc.
    :param velocity:    Velocity for the new note_on events (note_off uses 0).
    :param channel:     MIDI channel for these notes (0 = first channel).

    :return:            The same MidiFile object, but with Track 1 updated.
                        You can then save it via midi_file.save("updated.mid").
    """

    # Safety check: ensure the file has at least 2 tracks
    track = 0
    old_track1 = midi_file.tracks[track]

    # Create a new track to hold the preserved events + new note events
    new_track1 = MidiTrack()
    
    # 1) Copy all non-note messages from the old track 
    #    (e.g. control_change, program_change, pitchwheel, etc.), 
    #    skipping old note_on/note_off and end_of_track.
    for msg in old_track1:
        if msg.type in ('note_on', 'note_off', 'end_of_track'):
            # Skip old note messages and the old end_of_track
            continue
        new_track1.append(msg)

    # prev_note_num = None
    # running_sum = 0
    # count       = 0
    # for bar in bars_data:
    #     for pc, dur in bar:
    #         # Build the three candidates in each octave
    #         if prev_note_num is None:
    #             # First note: just map directly
    #             note_num = pitch_offset + pc
    #             print(note_num)
    #         else:
    #             # Compute running mean
    #             mean_ref = running_sum / count

    #             # Determine the octave-aligned candidates
    #             base_oct = prev_note_num - (prev_note_num % 12)
    #             candidates = [
    #                 base_oct + pc,
    #                 base_oct + pc + 12,
    #                 base_oct + pc - 12
    #             ]

    #             def score(n):
    #                 return 0.3 * abs(n - prev_note_num) + 0.6 * abs(pitch_offset + 6)

    #             note_num = min(candidates, key=score)
    #             print(note_num)

    for bar in bars_data:
        for pc, dur in bar:
            # Build the three candidates in each octave
                # First note: just map directly
            note_num = pitch_offset + pc
            # Note on, delta-time=0 from the previous message

            new_track1.append(Message(
                'note_on',
                channel=channel,
                note=note_num,
                velocity=velocity,
                time=0
            ))
            # Corresponding note off, delta-time = duration
            new_track1.append(Message(
                'note_off',
                channel=channel,
                note=note_num,
                velocity=0,
                time=dur
            ))
            # prev_note_num = note_num
            # running_sum += note_num
            # count      += 1

    # 3) Append a fresh end_of_track meta message
    new_track1.append(MetaMessage('end_of_track', time=0))

    # 4) Assign the new track back into the MidiFile

    midi_file.tracks[track] = new_track1

    return midi_file


def to_score(file, input_chords):
    us = environment.UserSettings()
    us['musicxmlPath'] = '/Applications/MuseScore4.app/Contents/MacOS/mscore'
    us['musescoreDirectPNGPath'] = '/Applications/MuseScore4.app/Contents/MacOS/mscore'
    score = converter.parse(file)
    part  = score.parts[0].makeNotation()
    
    # 2) strip out any existing KeySignature objects
    for ks in part.recurse().getElementsByClass(key.KeySignature):
        ks.activeSite.remove(ks)
    
    # 3) put your “Chords: …” line above measure 1
    progression = "   ‖   ".join(input_chords)
    txt = expressions.TextExpression(f"Chords: {progression}")
    txt.placement = "above"
    if part.measure(1):
        part.measure(1).insert(0, txt)
    else:
        part.insert(0.0, txt)
    
    # 4) for each bar, decide flats vs sharps by simple string‐matching
    for i, chord_name in enumerate(input_chords, start=1):
        meas = part.measure(i)
        if not meas:
            continue
        
        # extract root letter and optional accidental (# or b)
        m = re.match(r'^([A-Ga-g])([b#]?)', chord_name)
        if m:
            letter = m.group(1).upper()
            acc    = m.group(2)
        else:
            # fallback: treat as a natural
            letter, acc = chord_name[0].upper(), ''
        
        # decide spelling
        if acc == '#':
            use_sharps = True
        elif acc == 'b':
            use_sharps = False
        else:
            # naturals: C & F → flats; D, E, G, A, B → sharps
            use_sharps = False if letter in ('C', 'F') else True
        
        # respell every Note in that measure
        for n in meas.recurse().getElementsByClass(note.Note):
            p = n.pitch
            if use_sharps and 'b' in p.name:
                n.pitch = p.getEnharmonic()
            elif not use_sharps and '#' in p.name:
                n.pitch = p.getEnharmonic()
    
    return part

def prompt_for_file_path():
    """
    Prompt the user to enter a file name (searched in 'inputs/').
    Continues prompting until an existing file is found.
    
    Returns:
        The full file path (as a string).
    """
    while True:
        file_name = simpledialog.askstring(
            "File Path", 
            "Please enter the file name (it will be searched in 'inputs/'):"
        )
        # If the user cancels (None is returned), exit or return None.
        if file_name is None:
            return None
        file_name = file_name.strip()
        # Prepend the directory 'inputs/' if it isn't already included
        if not file_name.startswith("inputs" + os.sep):
            file_path = os.path.join("inputs", file_name)
        else:
            file_path = file_name

        if os.path.isfile(file_path):
            return file_path
        else:
            messagebox.showerror("File Not Found", f"'{file_path}' does not exist. Please try again.")

# --- Popup Prompt for Chord Progression ---
def prompt_for_chord_progression(num_bars):
    """
    Prompt the user to enter num_bars chord symbols delineated by commas.
    Continues prompting until the input has exactly num_bars valid chord symbols.
    
    Returns:
        A list of valid chord symbol strings.
    """
    while True:
        user_input = simpledialog.askstring(
            "Chord Progression", 
            f"Please enter {num_bars} chord symbols (separated by commas):"
        )
        # Allow the user to cancel.
        if user_input is None:
            return None

        chords_list = [chord.strip() for chord in user_input.split(',') if chord.strip()]

        if len(chords_list) != num_bars:
            messagebox.showerror(
                "Chord Count Error", 
                f"Error: You entered {len(chords_list)} chord(s), but {num_bars} chord(s) were expected. Please try again."
            )
            continue

        invalid_found = False
        for chord in chords_list:
            if not is_valid_chord(chord):
                messagebox.showerror(
                    "Invalid Chord", 
                    f"Invalid chord: '{chord}'.\nValid chord qualities are:\n{', '.join(ALLOWED_CHORD_QUALITIES)}\nPlease try again."
                )
                invalid_found = True
                break  # Exit on the first invalid chord

        if invalid_found:
            continue

        # All chords are valid.
        return chords_list

def is_valid_chord(chord_str):
    """
    Check whether a chord string is valid.
    
    A valid chord has:
      - A tonic: one of the note names A, B, C, D, E, F, or G with an optional sharp '#' or flat 'b'.
      - A chord quality that exactly matches one from the allowed list (case-insensitive).

    
    Returns:
        True if chord_str is valid; False otherwise.
    """
    # Define the allowed chord quality descriptors.

    # Normalize to lower-case for a case-insensitive comparison.
    allowed_qualities_set = {q.lower() for q in ALLOWED_CHORD_QUALITIES}
    
    # Define a regex pattern for the tonic: a letter A-G followed optionally by '#' or 'b'.
    pattern = r"^([A-G](?:#|b)?)(.*)$"
    match = re.match(pattern, chord_str)
    if not match:
        # The chord string doesn't start with a valid tonic.
        return False

    tonic = match.group(1)  # the first group is the tonic (e.g., "C", "F#", "Bb")
    quality = match.group(2).strip()  # everything else should be the chord quality descriptor

    # Per the given specification, a quality must be provided.
    if quality == "":
        return False

    # Check (case-insensitive) if the provided chord quality is in our allowed list.
    return quality.lower() in allowed_qualities_set

def create_bar_chords(input_chords):
    bar_chords = []
    for chord in input_chords: 
        bar_chords.append(chords.Chord(chord).get_notes())
    return bar_chords


# Map note names (tonic) to pitch-class integers
NOTE_NAME_TO_PC = {
    'C': 0,  'C#': 1, 'Db': 1,
    'D': 2,  'D#': 3, 'Eb': 3,
    'E': 4,  'Fb': 4, 'E#': 5, 'F': 5,
    'F#':6,  'Gb': 6,
    'G': 7,  'G#': 8, 'Ab': 8,
    'A': 9,  'A#':10, 'Bb':10,
    'B':11,  'Cb':11, 'B#': 0
}

# Canonical scale‑interval patterns (in semitones) for each chord quality
QUALITY_SCALE_INTERVALS = {
    # Major family
    'major':           [0,2,4,5,7,9,11],          # Ionian
    'maj7':            [0,2,4,5,7,9,11],          # same as major
    'Δ7':              [0,2,4,5,7,9,11],
    # Minor family
    'minor':           [0,2,3,5,7,8,10],          # Aeolian
    'm7':              [0,2,3,5,7,9,10],          # Dorian
    # Dominant 7th → Mixolydian
    '7':               [0,2,4,5,7,9,10],
    'dominant seventh':[0,2,4,5,7,9,10],
    # Half‑diminished (m7b5) → Locrian ♮2
    'm7b5':            [0,2,3,5,6,8,10],          # Locrian
    'half-diminished seventh':[0,2,3,5,6,8,10],
    'ø':               [0,2,3,5,6,8,10],
    # Fully diminished seventh → diminished “octatonic” (W‑H)
    'dim7':            [0,2,3,5,6,8,9,11],        # whole‑half
    'diminished seventh':[0,2,3,5,6,8,9,11],
    '°':               [0,2,3,5,6,8,9,11],
    # Augmented triad → augmented hexatonic
    'aug':             [0,2,4,6,8,10],            # whole‑tone
    'augmented':       [0,2,4,6,8,10],
    '+':               [0,2,4,6,8,10],
    # Augmented major 7th → Lydian augmented
    'maj7#5':          [0,2,4,6,7,9,11],
    'augmented major seventh':[0,2,4,6,7,9,11],
    # Minor‑major seventh → melodic minor
    'mM7':             [0,2,3,5,7,9,11],
    'minor major seventh':[0,2,3,5,7,9,11],
}

# Map all ALLOWED_CHORD_QUALITIES to a canonical key in QUALITY_SCALE_INTERVALS
QUALITY_CANONICAL = {
    # major synonyms
    **dict.fromkeys(['M','major','maj','Δ'], 'major'),
    # minor synonyms
    **dict.fromkeys(['m','minor','min','-'], 'minor'),
    # maj7 synonyms
    **dict.fromkeys(['M7','maj7','Δ7'], 'maj7'),
    # dominant seventh
    **dict.fromkeys(['7','dominant seventh'], '7'),
    # m7 synonyms
    **dict.fromkeys(['m7','minor seventh','-7'], 'm7'),
    # half‑diminished
    **dict.fromkeys(['m7b5','half-diminished seventh','-7b5','ø','mb5','-b5'], 'm7b5'),
    # diminished seventh
    **dict.fromkeys(['dim7','diminished seventh','°'], 'dim7'),
    # augmented
    **dict.fromkeys(['A','augmented','aug','+'], 'aug'),
    # augmented seventh
    **dict.fromkeys(['aug7','augmented seventh','+7'], 'aug'),
    # augmented major seventh
    **dict.fromkeys(['maj7#5','augmented major seventh','+M7','+Δ7'], 'maj7#5'),
    # minor‑major seventh
    **dict.fromkeys(['mM7','m maj7','mΔ7','-Δ7'], 'mM7'),
}

def chord_to_scale_degrees(chord_str):
    """
    Given a chord string like "Cmaj7#5" or "Dm7b5", return the corresponding
    diatonic scale (list of pitch-classes 0–11) based on quality.
    """
    # 1) Split tonic vs. quality
    m = re.match(r'^([A-G](?:#|b)?)(.*)$', chord_str.strip())
    if not m:
        raise ValueError(f"Cannot parse chord '{chord_str}'")
    tonic_name, quality = m.group(1), m.group(2).strip()
    tonic_pc = NOTE_NAME_TO_PC.get(tonic_name)
    if tonic_pc is None:
        raise ValueError(f"Unknown tonic '{tonic_name}' in '{chord_str}'")
    # 2) Find canonical quality key
    q_key = QUALITY_CANONICAL.get(quality.lower())
    if q_key is None:
        raise ValueError(f"Unknown chord quality '{quality}' in '{chord_str}'")
    # 3) Get interval pattern, build scale degrees
    intervals = QUALITY_SCALE_INTERVALS[q_key]
    return [(tonic_pc + i) % 12 for i in intervals]