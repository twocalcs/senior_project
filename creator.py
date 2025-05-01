#!/usr/bin/env python3
import numpy as np
import random
from musicaiz.rhythm import NoteLengths
from parser import LickParser
from typing import Dict

class Creator:
    def __init__(self, parser):
        self.parser = parser
        self.T_pitch = parser.modified_pitch_matrices
        self.T_length = parser.note_length_matrix

        self.bar_length = parser.bar_length_ticks
        self.num_bars = len(parser.all_bars)
        self.tick_mapping = self.map_index_to_tick_length(self.bar_length, triplets=True)
        # print(self.tick_mapping)


    def sample_joint_markov_chain(self, start_state, length, bar_num):
        states = [start_state]
        for _ in range(length):
            current_pitch, current_length = states[-1]

            # Sample next pitch
            weights_pitch = self.T_pitch[bar_num][current_pitch, :].copy()
            if weights_pitch.sum() == 0:
                weights_pitch = np.ones_like(weights_pitch)
            weights_pitch /= weights_pitch.sum()
            next_pitch = np.random.choice(len(weights_pitch), p=weights_pitch)

            # Sample next note length
            weights_length = self.T_length[current_length, :].copy()
            if weights_length.sum() == 0:
                weights_length = np.ones_like(weights_length)
            weights_length /= weights_length.sum()
            next_length = np.random.choice(len(weights_length), p=weights_length)

            states.append((next_pitch, next_length))
        return states[1:]

    def generate_bar(self, start_state, bar_num):
        bar = []
        total_ticks = 0
        current_state = start_state

        while total_ticks < self.bar_length:
            next_state = self.sample_joint_markov_chain(current_state, 1, bar_num)[0]
            pitch, note_length_index = next_state
            tick_duration = self.tick_mapping[note_length_index]
            
            if total_ticks + tick_duration > self.bar_length:
                tick_duration = self.bar_length - total_ticks
            
            bar.append((pitch, tick_duration))
            total_ticks += tick_duration
            
            current_state = (pitch, note_length_index)
        
        return bar, current_state

    def regenerate(self):
        bars = []
        start_pitch = random.choice(self.parser.bar_chords[0])
        allowed_indices = [1, 2, 3, 4, 5, 7]
        start_length = random.choice(allowed_indices)
        start_state = (start_pitch, start_length)
        for i in range(self.num_bars):
            bar, final_state = self.generate_bar(start_state, i)
            bars.append(bar)
            start_state = final_state
        # print(bars)
        return bars


    def map_index_to_tick_length(self, bar_length: int, triplets: bool) -> Dict[int, int]:
        mapping = {}
        # Iterate over the NoteLengths enum in declaration order.
        for idx, note_name in enumerate(NoteLengths.__members__.keys()):
            # Optionally skip triplet durations.
            if not triplets and "TRIPLET" in note_name:
                continue
            note = NoteLengths[note_name]
            # Compute tick length. In 4/4, a whole note's tick value should equal bar_length.
            tick_value = round(bar_length * note.fraction)
            mapping[idx] = tick_value
        return mapping