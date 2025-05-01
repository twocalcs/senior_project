import os, sys, mido
from musicaiz.loaders import Musa
from typing import List
from parser import LickParser
from creator import Creator
from embellisher import Embellisher
import helpers

# ---------- reusable worker --------------------------------------------------
def run_single(file_path: str, chord_progression: List[str], out_dir: str = "outputs"):
    musa = Musa(file_path)
    mid  = mido.MidiFile(file_path)
    num_bars = len(musa.bars)

    if len(chord_progression) != num_bars:
        raise ValueError(
            f"{os.path.basename(file_path)}: expected {num_bars} chords but got {len(chord_progression)}"
        )

    bar_chords = helpers.create_bar_chords(chord_progression)
    pitch_map = {
        "C": 0, "B#": 0, "C#": 1, "Db": 1,  "D": 2,  "D#": 3, "Eb": 3,
        "E": 4, "Fb": 4, "E#": 5, "F": 5,  "F#": 6, "Gb": 6,  "G": 7,
        "G#": 8, "Ab": 8, "A": 9, "A#":10, "Bb":10, "B":11,  "Cb":11
    }
    bar_chords = [[pitch_map[n] for n in chord] for chord in bar_chords]

    notes   = musa.get_notes_in_bars(0, num_bars)
    parser  = LickParser(bar_length_ticks=1920,
                         input_chords=chord_progression,
                         bar_chords=bar_chords,
                         notes=notes)
    creator = Creator(parser)
    emb     = Embellisher(creator)
    result  = emb.embellish(mid)

    os.makedirs(out_dir, exist_ok=True)
    stem        = os.path.splitext(os.path.basename(file_path))[0]
    out_mid     = os.path.join(out_dir, f"{stem}_embellished.mid")
    result.save(out_mid)
    print(f"{stem} --> {out_mid}")

# ---------- batch driver -----------------------------------------------------
def main():
    in_dir = "inputs"
    out_dir = "outputs"

    for entry in sorted(os.listdir(in_dir)):
        if not entry.lower().endswith(".mid"):
            continue

        midi_path = os.path.join(in_dir, entry)
        chords_path = os.path.splitext(midi_path)[0] + ".chords"

        if not os.path.exists(chords_path):
            print(f"{entry}: skipped (no {os.path.basename(chords_path)})")
            continue

        with open(chords_path) as fh:
            chord_progression = [c.strip() for c in fh.read().split(',') if c.strip()]

        try:
            run_single(midi_path, chord_progression, out_dir)
        except Exception as e:
            print(f"{entry}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
