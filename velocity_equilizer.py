import mido

mid = mido.MidiFile("inputs/test2.mid")

for track in mid.tracks:
    for msg in track:
        if msg.type == "note_on":
            msg.velocity = 60

mid.save("test.mid")

for i, track in enumerate(mid.tracks):
    print(f"Track {i}: {track.name}")
    for msg in track:
        print(msg)