# lick_parser.py

from musicaiz.loaders import Musa
from musicaiz.features import pitch, rhythm
from musicaiz.harmony import chords, ChordQualities
from itertools import product
import random
import numpy as np
from helpers import chord_to_scale_degrees

class LickParser:
    def __init__(self, bar_length_ticks=1920, input_chords=None, bar_chords=None, notes=None):
        self.bar_length_ticks = bar_length_ticks
        self.input_chords = input_chords
        self.bar_chords = bar_chords
        self.notes = notes
        self.all_bars = self.split_into_bars(self.notes)
        # print("All Bars:")
        # for i, bar in enumerate(self.all_bars):
        #     print(f"Bar {i}: {[self.midi_to_note_name(n.pitch) for n in bar]}")
        self.raw_pitch_matrix = pitch.pitch_class_transition_matrix(notes)
        mat = pitch.pitch_class_transition_matrix(self.all_bars[0])
        # print(type(mat), mat)
        self.convert_pitch_count_to_prob_matrix(mat, self.bar_chords[0],)
        self.pitch_matrices_per_bar = [
            self.convert_pitch_count_to_prob_matrix(
                pitch.pitch_class_transition_matrix(n), 
                self.bar_chords[i]
            )
            for i, n in enumerate(self.all_bars)
        ]

        self.modified_pitch_matrices = self.recreate_matrices()
        self.note_length_matrix = self.convert_length_counts_to_prob_matrix(rhythm.note_length_transition_matrix(notes))
        # print(self.pitch_matrices_per_bar)
        # print(self.note_length_matrix)
        # Filter the bars to only include notes matching the chord tones.
        # self.parsed_bars = self.get_chord_tones(self.all_bars)
        # print("\nParsed Bars (only chord tones):")
        # for i, bar in enumerate(self.parsed_bars):
        #     print(f"Bar {i}: {[self.midi_to_note_name(n.pitch) for n in bar]}")
        # self.fixed_points =self.choose_fixed_points()
        # print(rhythm.note_length_transition_matrix(notes))
        # print(pitch.pitch_class_transition_matrix(notes))

    def recreate_matrices(self, alpha=0.85):
        new_matrices = []

        for bar_idx, bar_mat in enumerate(self.pitch_matrices_per_bar):
            combined = alpha * bar_mat + (1 - alpha) * self.raw_pitch_matrix.copy()
            chord_str = self.input_chords[bar_idx]
            scale_degrees = set(chord_to_scale_degrees(chord_str))
            n = combined.shape[0]

            for i in range(n):
                for j in range(n):
                    if j not in scale_degrees:
                        combined[i, j] = 0.0

            for i in range(n):
                row = combined[i]
                s = row.sum()
                if s > 0:
                    combined[i] = row / s
                else:
                    mask = [1 if j in scale_degrees else 0 for j in range(n)]
                    total = sum(mask)
                    if total:
                        combined[i] = [m/total for m in mask]

            new_matrices.append(combined)
        # print(new_matrices)
        return new_matrices
    
        
    def convert_pitch_count_to_prob_matrix(self, matrix, chord_tones):
        # print(type(matrix))
        n = matrix.shape[0]

        col_sums = matrix.sum(axis=0)
        valid_cols = np.where(col_sums > 0)[0]

        for i in range(n):
            row_sum = matrix[i].sum()
            if row_sum > 0:
                matrix[i] /= row_sum
            else:
                if len(valid_cols) > 0:
                    fallback_row = np.zeros(n)
                    fallback_row[valid_cols] = 1.0
                    fallback_row /= fallback_row.sum()
                    matrix[i] = fallback_row
                else:
                    matrix[i] = 1.0 / n
        return matrix
    def convert_length_counts_to_prob_matrix(self, matrix):
        # print(type(matrix))
        n = matrix.shape[0]

        col_sums = matrix.sum(axis=0)
        valid_cols = np.where(col_sums > 0)[0]


        for i in range(n):
            row_sum = matrix[i].sum()
            if row_sum > 0:
                
                matrix[i] /= row_sum
            else:
            
                if len(valid_cols) > 0:
                    fallback_row = np.zeros(n)
                    fallback_row[valid_cols] = 1.0
                    fallback_row /= fallback_row.sum()
                    matrix[i] = fallback_row
                else:
                    matrix[i] = 1.0 / n
        # print(matrix)
        return matrix

    
    def midi_to_note_name(self, pitch):
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        if isinstance(pitch, int):
            return note_names[pitch % 12]
        else:
            return pitch

    def index_to_note_length(self, index: int, triplets: bool = True) -> str:
        if triplets:
            note_lengths = [
                "DOTTED_WHOLE",     # index 0
                "WHOLE",            # index 1
                "DOTTED_HALF",      # index 2
                "HALF",             # index 3
                "DOTTED_QUARTER",   # index 4
                "QUARTER",          # index 5
                "DOTTED_EIGHT",     # index 6
                "EIGHT",            # index 7
                "DOTTED_SIXTEENTH", # index 8
                "SIXTEENTH",        # index 9
                "DOTTED_THIRTY_SECOND", # index 10
                "THIRTY_SECOND",    # index 11
                "DOTTED_SIXTY_FOUR",# index 12
                "SIXTY_FOUR",       # index 13
                "DOTTED_HUNDRED_TWENTY_EIGHT", # index 14
                "HUNDRED_TWENTY_EIGHT",        # index 15
                "HALF_TRIPLET",     # index 16
                "QUARTER_TRIPLET",  # index 17
                "EIGHT_TRIPLET",    # index 18
                "SIXTEENTH_TRIPLET" # index 19
            ]
        else:
            note_lengths = [
                "DOTTED_WHOLE",     # index 0
                "WHOLE",            # index 1
                "DOTTED_HALF",      # index 2
                "HALF",             # index 3
                "DOTTED_QUARTER",   # index 4
                "QUARTER",          # index 5
                "DOTTED_EIGHT",     # index 6
                "EIGHT",            # index 7
                "DOTTED_SIXTEENTH", # index 8
                "SIXTEENTH",        # index 9
                "DOTTED_THIRTY_SECOND", # index 10
                "THIRTY_SECOND",    # index 11
                "DOTTED_SIXTY_FOUR",# index 12
                "SIXTY_FOUR",       # index 13
                "DOTTED_HUNDRED_TWENTY_EIGHT", # index 14
                "HUNDRED_TWENTY_EIGHT"         # index 15
            ]
        if isinstance(index, int) and 0 <= index < len(note_lengths):
            return note_lengths[index]
        else:
            return str(index)


    def get_transition_notes(self):
        transition_notes = []

        for i in range(len(self.bar_chords) - 1):  
            current_chord = self.bar_chords[i]
            next_chord = self.bar_chords[i + 1]

            chord_pairs = []
            
            for note1, note2 in product(current_chord, next_chord):
                if note1 == note2 or abs(note1 - note2) in {1, 2}: 
                    chord_pairs.append((note1, note2))
            
            transition_notes.append(chord_pairs)

        return transition_notes


    def choose_fixed_points(self):
        fixed_points = self.find_fixed_points()

        for i in range(len(fixed_points)):
            chord_tones = {note for note in self.parsed_bars[i]}  
            # print(chord_tones)
            existing_fixed_notes = set(fixed_points[i])
            # print(existing_fixed_notes) 

            while len(fixed_points[i]) < 2:
                candidates = list(chord_tones - existing_fixed_notes)

                if not candidates:
                    break 

                random.shuffle(candidates)

                distance_weights = []
                for candidate in candidates:
                    distances = [abs(candidate.start_ticks - fixed_note.start_ticks) for fixed_note in existing_fixed_notes]
                    avg_distance = sum(distances) / len(distances) if distances else 1
                    distance_weights.append(avg_distance) 

                total_weight = sum(distance_weights)
                if total_weight > 0:
                    distance_weights = [w / total_weight for w in distance_weights]
                else:
                    distance_weights = [1 / len(candidates)] * len(candidates) 
                new_fixed_note = random.choices(candidates, weights=distance_weights, k=1)[0]

                fixed_points[i].append(new_fixed_note)
                existing_fixed_notes.add(new_fixed_note)
        # print("Fixed Points:", [[[n.pitch for n in bar] for bar in fixed_points]])
        return fixed_points



    def find_fixed_points(self):
        transition_notes = self.get_transition_notes()
        fixed_points = [[] for _ in range(len(self.parsed_bars))]

        for i in range(len(self.parsed_bars) - 1):
            last_note = self.parsed_bars[i][-1]
            first_note = self.parsed_bars[i + 1][0]

            last_pitch = last_note.pitch % 12 
            first_pitch = first_note.pitch % 12
            if i < len(transition_notes) and (last_pitch, first_pitch) in transition_notes[i]:
                fixed_points[i].append(last_note)   
                fixed_points[i + 1].append(first_note)

        # print("Found Fixed Points:", [[[n.pitch for n in bar] for bar in fixed_points]])
        return fixed_points

    

    def split_into_bars(self, notes):
        max_bar_index = max(note.start_ticks // self.bar_length_ticks for note in notes)
        all_bars = [[] for _ in range(max_bar_index + 1)]
        for note in notes:
            bar_idx = note.start_ticks // self.bar_length_ticks
            all_bars[bar_idx].append(note)
        return all_bars

    def get_chord_tones(self, all_bars):
        if self.bar_chords is None:
            raise ValueError("bar_chords must be provided to filter chord tones.")
        if len(self.bar_chords) < len(all_bars):
            raise ValueError("Not enough chord tone definitions for the number of bars.")
        
        chord_tones = [[] for _ in range(len(all_bars))]
        for i, bar in enumerate(all_bars):
            for note in bar:
                note_name = note.pitch % 12
                if note_name in self.bar_chords[i]:
                    chord_tones[i].append(note)
        return chord_tones