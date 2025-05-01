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
    track = 0
    old_track1 = midi_file.tracks[track]

    new_track1 = MidiTrack()
    for msg in old_track1:
        if msg.type in ('note_on', 'note_off', 'end_of_track'):
            # Skip old note messages and the old end_of_track
            continue
        new_track1.append(msg)

    last_note_num = 0
    for bar in bars_data:
        for pc, dur in bar:
            note_num = pitch_offset + pc

            if last_note_num in (60, 61) and note_num in (70, 71):
                note_num -= 12                    

            last_note_num = note_num
            new_track1.append(Message(
                'note_on',
                channel=channel,
                note=note_num,
                velocity=velocity,
                time=0
            ))
        
            new_track1.append(Message(
                'note_off',
                channel=channel,
                note=note_num,
                velocity=0,
                time=dur
            ))
    
    
    new_track1.append(MetaMessage('end_of_track', time=0))

    midi_file.tracks[track] = new_track1

    return midi_file


def to_score(file, input_chords):
    us = environment.UserSettings()
    us['musicxmlPath'] = '/Applications/MuseScore4.app/Contents/MacOS/mscore'
    us['musescoreDirectPNGPath'] = '/Applications/MuseScore4.app/Contents/MacOS/mscore'
    score = converter.parse(file)
    part  = score.parts[0].makeNotation()

    for ks in part.recurse().getElementsByClass(key.KeySignature):
        ks.activeSite.remove(ks)
    
    progression = "   ‖   ".join(input_chords)
    txt = expressions.TextExpression(f"Chords: {progression}")
    txt.placement = "above"
    if part.measure(1):
        part.measure(1).insert(0, txt)
    else:
        part.insert(0.0, txt)
    
    for i, chord_name in enumerate(input_chords, start=1):
        meas = part.measure(i)
        if not meas:
            continue
        
        m = re.match(r'^([A-Ga-g])([b#]?)', chord_name)
        if m:
            letter = m.group(1).upper()
            acc    = m.group(2)
        else:
            letter, acc = chord_name[0].upper(), ''
        if acc == '#':
            use_sharps = True
        elif acc == 'b':
            use_sharps = False
        else:
            use_sharps = False if letter in ('C', 'F') else True
    
        for n in meas.recurse().getElementsByClass(note.Note):
            p = n.pitch
            if use_sharps and 'b' in p.name:
                n.pitch = p.getEnharmonic()
            elif not use_sharps and '#' in p.name:
                n.pitch = p.getEnharmonic()
    
    return part

def prompt_for_file_path():
    while True:
        file_name = simpledialog.askstring(
            "File Path", 
            "Please enter the file name (it will be searched in 'inputs/'):"
        )
        if file_name is None:
            return None
        file_name = file_name.strip()
        if not file_name.startswith("inputs" + os.sep):
            file_path = os.path.join("inputs", file_name)
        else:
            file_path = file_name

        if os.path.isfile(file_path):
            return file_path
        else:
            messagebox.showerror("File Not Found", f"'{file_path}' does not exist. Please try again.")

def prompt_for_chord_progression(num_bars):
    while True:
        user_input = simpledialog.askstring(
            "Chord Progression", 
            f"Please enter {num_bars} chord symbols (separated by commas):"
        )
        # Allow the user to cancel
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
                break  # Exit on invalid chord

        if invalid_found:
            continue

        return chords_list

def is_valid_chord(chord_str):
    allowed_qualities_set = {q.lower() for q in ALLOWED_CHORD_QUALITIES}
    
    # Define a regex pattern for the tonic: a letter A-G followed optionally by '#' or 'b'.
    pattern = r"^([A-G](?:#|b)?)(.*)$"
    match = re.match(pattern, chord_str)
    if not match:
        # The chord string doesn't start with a valid tonic.
        return False

    tonic = match.group(1) 
    quality = match.group(2).strip() 

    if quality == "":
        return False

    return quality.lower() in allowed_qualities_set

def create_bar_chords(input_chords):
    bar_chords = []
    for chord in input_chords: 
        bar_chords.append(chords.Chord(chord).get_notes())
    return bar_chords

NOTE_NAME_TO_PC = {
    'C': 0,  'C#': 1, 'Db': 1,
    'D': 2,  'D#': 3, 'Eb': 3,
    'E': 4,  'Fb': 4, 'E#': 5, 'F': 5,
    'F#':6,  'Gb': 6,
    'G': 7,  'G#': 8, 'Ab': 8,
    'A': 9,  'A#':10, 'Bb':10,
    'B':11,  'Cb':11, 'B#': 0
}

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
    m = re.match(r'^([A-G](?:#|b)?)(.*)$', chord_str.strip())
    if not m:
        raise ValueError(f"Cannot parse chord '{chord_str}'")
    tonic_name, quality = m.group(1), m.group(2).strip()
    tonic_pc = NOTE_NAME_TO_PC.get(tonic_name)
    if tonic_pc is None:
        raise ValueError(f"Unknown tonic '{tonic_name}' in '{chord_str}'")
    
    q_key = QUALITY_CANONICAL.get(quality.lower())
    if q_key is None:
        raise ValueError(f"Unknown chord quality '{quality}' in '{chord_str}'")

    intervals = QUALITY_SCALE_INTERVALS[q_key]
    return [(tonic_pc + i) % 12 for i in intervals]