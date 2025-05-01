import creator
import helpers
import random
class Embellisher:
    def __init__(self, creator):
        self.creator = creator
        self.bars = creator.regenerate()
        # self.bars = creator.parser.all_bars
        self.bar_length = creator.bar_length

    def embellish(self, mido_file):
        self.bars = self.add_triplets(self.bars)
        # print(self.bars)
        result = helpers.update_track_in_midi_file(mido_file, self.bars, 60, 60, 0)
        
        return result

    def add_triplets(self, bars):
        quarter_length = self.bar_length // 4
        triplet_bars = []
        trip_len = quarter_length // 3

        for bar_idx, bar in enumerate(self.bars):
            new_bar = []
            chord_tones = set(self.creator.parser.bar_chords[bar_idx])
            scale       = helpers.chord_to_scale_degrees(self.creator.parser.input_chords[bar_idx])
            curr_spot = 0
            for i, (pc, length) in enumerate(bar):
                did_triplet = False
                if length == quarter_length and curr_spot % quarter_length == 0:
                    if random.random() < 1:
                        if i + 1 < len(bar):
                            next_pc = bar[i + 1][0]
                            is_step_up   = (scale.index(next_pc)- scale.index(pc)) ==  1
                            is_step_down = (scale.index(next_pc) - scale.index(pc)) == -1
                            if (
                                next_pc in chord_tones
                                and pc in scale
                                and next_pc in scale
                                and (is_step_down or is_step_up)
                            ):
                                idx      = scale.index(pc)
                                if is_step_up:
                                    up_pitch = scale[(idx - 1) % len(scale)]
                                else:
                                    up_pitch = scale[(idx + 1) % len(scale)]
                                new_bar.extend([
                                    (pc,      trip_len),
                                    (up_pitch,trip_len),
                                    (pc,      trip_len),
                                ])
                                did_triplet = True
                if not did_triplet:
                    new_bar.append((pc, length))
                    curr_spot += length

            triplet_bars.append(new_bar)

        return triplet_bars