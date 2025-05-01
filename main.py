import mido
from musicaiz.loaders import Musa
from musicaiz.harmony import chords, ChordQualities
from musicaiz.features import rhythm 
from parser import LickParser
from creator import Creator
from embellisher import Embellisher
import helpers
import sys
import argparse
import tkinter as tk
from tkinter import simpledialog, messagebox
debug = 0

if debug == 0:
    root = tk.Tk()
    root.withdraw()
        
    # Prompt for file path.
    file_path = helpers.prompt_for_file_path()
    if file_path is None:
        messagebox.showinfo("Cancelled", "No file selected. Exiting.")
        exit(0)
    musa = Musa(file_path)
    mid = mido.MidiFile(file_path)
    num_bars = len(musa.bars)


    chord_progression = helpers.prompt_for_chord_progression(num_bars)
    if chord_progression is None:
        messagebox.showinfo("Cancelled", "No chord progression provided. Exiting.")
        exit(0)

else:
    file_path = "inputs/ex1.mid"
    musa = Musa(file_path)
    mid = mido.MidiFile(file_path)

    num_bars = len(musa.bars)
    # chord_progression = ["Cmaj7", "Ebmaj7", "Abmaj7", "Dbmaj7", "Cmaj7", "Cmaj7"]
    chord_progression = ["Dm7", "G7", "Cmaj7"]

if len(chord_progression) != num_bars:
    print(f"Error: expected {num_bars} chords but got {len(chord_progression)}",
            file=sys.stderr)
    sys.exit(1)

bar_chords = helpers.create_bar_chords(chord_progression)
pitch_map = {
    "C": 0,
    "B#": 0,
    "C#": 1,
    "Db": 1, 
    "D": 2,
    "D#": 3,
    "Eb": 3, 
    "E": 4,
    "Fb": 4,  
    "E#": 5,  
    "F": 5,
    "F#": 6,
    "Gb": 6, 
    "G": 7,
    "G#": 8,
    "Ab": 8, 
    "A": 9,
    "A#": 10,
    "Bb": 10, 
    "B": 11,
    "Cb": 11 
}


# print(bar_chords)
bar_chords = [[pitch_map[note] for note in chord] for chord in bar_chords]

notes = musa.get_notes_in_bars(0,num_bars)
parser = LickParser(bar_length_ticks=1920, input_chords = chord_progression, bar_chords=bar_chords, notes = notes)
# print(parser.get_rhythms())
creator = Creator(parser)
reverse_mapping = {tick: idx for idx, tick in creator.tick_mapping.items()}
# converted = [[(parser.midi_to_note_name(p),
#                parser.index_to_note_length(min(creator.tick_mapping.items(), key=lambda x: abs(x[1]-n))[0]))
#               for p, n in bar] for bar in creator.regenerate()]

embellisher_object = Embellisher(creator)
result = embellisher_object.embellish(mid)
mid.save("outputs/test.mid")

helpers.to_score("outputs/test.mid", chord_progression).show()
# helpers.to_score("inputs/test2.mid").show()