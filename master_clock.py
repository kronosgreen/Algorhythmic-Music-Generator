#
#
#   Algorhythmic Music Generator
#
#   Description:
#
#

import time
import rtmidi
import numpy as np
import random

# Setting up Music Theory
key_roots = {
    "C": 48,
    "Db": 49,
    "D": 50,
    "Eb": 51,
    "E": 52,
    "F": 53,
    "Gb": 54,
    "G": 55,
    "Ab": 56,
    "A": 57,
    "Bb": 58,
    "B": 59
}

major_pentatonic = np.array([0, 2, 4, 7, 9, 12, 0, 7])
minor_blues = np.array([0, 3, 5, 6, 7, 10, 12, 6])
major_scale = np.array([0, 2, 4, 5, 7, 9, 11, 12])
minor_scale = np.array([0, 2, 3, 5, 7, 8, 10, 12])
minor_pentatonic = np.array([0, 3, 5, 7, 10, 12, 0, 15])
harmonic_minor_scale = np.array([0, 2, 3, 5, 7, 8, 11, 12])
altered_scale = np.array([0, 1, 3, 4, 6, 8, 10, 12])
diminished_scale = np.array([0, 2, 3, 5, 6, 8, 9, 11])
scales = np.array([major_pentatonic, major_scale, minor_blues, minor_scale,
                   minor_pentatonic, harmonic_minor_scale, altered_scale, diminished_scale])

# chords in terms of intervals
major_triad = np.array([0, 7, 12, 16])
minor_7 = np.array([0, 7, 10, 15])
major_7 = np.array([0, 7, 11, 16])
major_5 = np.array([0, 4, 7, 12])
dom_7 = np.array([4, 10, 12, 19])
dim_7 = np.array([2, 9, 11, 17])
stacked_fifths = np.array([-12, 0, 7, 14])
# what chords correspond to scales I to VII
major_chords = np.array([major_5, minor_7, minor_7, major_5, dom_7 - 12, minor_7 - 12, dim_7 - 12])
minor_chords = np.array([minor_7, dim_7, major_7, minor_7 - 12, minor_7 - 12, major_7 - 12, dom_7 - 12])

mode_chords = np.array([major_chords, minor_chords])
# Set up priority of chords
chord_priority = [0, 3, 4, 1, 5, 2, 6]

# Set tempo
tempo = 120
subdivs = 16
num_inst = 6
midiout = rtmidi.MidiOut()
# print(midiout.get_ports())

midiout.open_port(2)

subdivisions = int(subdivs / 4)
counter = 0

# Create Note Map that dictates what will play
note_map = np.zeros((num_inst, subdivs))

# Set REST TIME between subdivisions
bpm = sleep_time = 60 / (tempo * subdivisions)
offset = 0

for i in range(0, subdivs, subdivisions):
    note_map[0, i] = 1
for i in range(subdivisions, subdivs, subdivisions*2):
    note_map[1, i] = 1
note_map[5, 0] = 1

# Single Downbeat
single_beat = np.array(1)

key = key_roots["F"]
scale = 1
key_notes = key + scales[scale]
subdiv_level = [8, 8, 8, 4, 4, 4, 4, 4, 4, 2, 2, 2, 2, 2, 1, 1]
playing_chord = -1
playing_bass = -1
playing_note = -1
melody_note = 0
chord_root = 0
index_counter = 0
octave = 0
mode = 1
intensity = -1
intensity_cat = 0
resolved = False


def clamp(n, minn, maxn):
    return max(min(maxn, n), minn)


def get_input():
    f = open("fancy-out.txt", 'r')
    fp = f.read().splitlines()
    f.close()
    return [int(x) for x in fp[len(fp) - 1].split(',')]


def clear_channels():
    for channel in range(num_inst):
        for i in range(127):
            midiout.send_message([128 + channel, i, 0])


# Drums
def send_drums(note):
    midiout.send_message([0x90, note, random.randint(64, 112)])
    midiout.send_message([0x80, note, 0])


# Chords
def send_chords(on, note):
    if on:
        midiout.send_message([0x91, note, 112])
    else:
        midiout.send_message([0x81, note, 0])


def play_chords(on, chord):
    if on:
        global playing_chord
        if playing_chord != -1:
            for n in mode_chords[mode, playing_chord]:
                send_chords(False, key_notes[playing_chord] + n)
        playing_chord = chord
    else:
        playing_chord = -1
    for n in mode_chords[mode, chord]:
        send_chords(on, key_notes[chord] + n)


# Lead Melody
def play_lead(on, note):
    global playing_note
    if on:
        if playing_note != -1:
            midiout.send_message([0x82, playing_note, 0])
        playing_note = note + octave * 12
        midiout.send_message([0x92, note + octave * 12, random.randint(64, 112)])
    else:
        if playing_note != -1:
            midiout.send_message(([0x82, playing_note, 0]))
        playing_note = -1


# Bass
def send_bass(note):
    midiout.send_message([0x93, note, 112])
    global playing_bass
    if playing_bass != -1:
        midiout.send_message([0x83, playing_bass, 0])
        playing_bass = note
    midiout.send_message([0x93, note, 112])


# Pads - on is entered as int 1 / 0
def send_pads(on):
    for n in key + stacked_fifths:
        midiout.send_message([0x84 + 16 * on, key_notes[0] - 24 + n, 112])
        midiout.send_message([0x94 + 16 * on, key_notes[0] - 24 + n, 112])


def key_change(new_key, new_scale):
    print("Changing to " + new_key)
    clear_channels()
    global key
    global key_notes
    global scale
    global mode
    key = key_roots[new_key]
    scale = new_scale
    mode = 0
    key_notes = key + scales[new_scale]


def update_note_map(sdiv, index):
    # updating notes
    # Gonna be super fucking complicated

    # Get global variables
    global intensity
    global octave
    global chord_root
    global chord_priority
    global scale
    global key_notes
    global intensity_cat
    global resolved

    # latest_sensor_data = get_input()

    # melody
    note_on = random.randrange(-1, 2, 2)
    note_length = random.randint(2, 6)

    # Change Melody
    if random.random() < 0.7:
        melody_note_change = random.randint(-2, 2)
        if melody_note_change == 0:
            melody_note_change = random.randint(-1, 1)
        global melody_note
        melody_note = (melody_note + melody_note_change) % 8
        note_map[4, sdiv] = note_on
        note_map[4, min(sdiv + 1, subdivs - 1): sdiv + note_length - 1] = 0
        note_map[4, min(sdiv + 3*note_length, subdivs - 1)] = -note_on
    # Change Chord Longer
    if random.random() < 0.35:
        note_map[3, sdiv] = note_on
        note_map[3, min(sdiv + 1, subdivs - 1):min(sdiv + 3*note_length, subdivs - 1)] = 0
        note_map[3, min(sdiv + 1, subdivs - 1):min(sdiv + 3*note_length, subdivs - 1)] = 0

    if not resolved:
        intens_change_prob = random.random()
        if intens_change_prob < 0.05:
            intensity = clamp(intensity - 1, 0, 15)
            print("Intensity: " + str(intensity))
        elif intens_change_prob < 0.30:
            intensity = clamp(intensity + 1, 0, 15)
            print("Intensity: " + str(intensity))

    if intensity < 2:
        if intensity_cat != 0:
            # turn on/off hi hats
            note_map[2, ] = np.repeat(0, subdivs)
            chord_root = chord_priority[0]
            clear_channels()
            intensity_cat = 0
            octave = 0
            # Minor Pentatonic Scale
            scale = 4
            key_notes = key + scales[scale]
    elif intensity < 5:
        chord_root = chord_priority[random.randint(0, 2)]
        if intensity_cat != 1:
            # turn on/off hi hats
            note_map[2, ] = np.repeat(0, subdivs)
            # randomly distribute kicks
            note_map[0, range(0, subdivs, int(subdivisions/2))] = random.randint(0, 1)
            clear_channels()
            intensity_cat = 1
            octave = 1
            # Minor Blues Scale
            scale = 2
            key_notes = key + scales[scale]
    elif intensity < 8:
        chord_root = chord_priority[random.randint(0, 4)]
        if intensity_cat != 2:
            # turn on/off hi hats
            note_map[2, ] = np.repeat(random.randint(0, 1), subdivs)
            octave = 1
            clear_channels()
            # randomly distribute kicks
            note_map[0, range(0, subdivs, int(subdivisions/2))] = random.randint(0, 1)
            # Set bass line
            note_map[5, ] = np.repeat([1, 0, 1, 0], subdivs/4)
            # set intensity category
            intensity_cat = 2
            # Harmonic Minor
            scale = 5
            key_notes = key + scales[scale]
    elif intensity < 11:
        chord_root = chord_priority[random.randint(0, 4)]
        if intensity_cat != 3:
            # turn on/off hi hats
            note_map[2, ] = np.repeat(random.randint(0, 1), subdivs)
            octave = 1
            clear_channels()
            # randomly distribute kicks
            note_map[0, range(0, subdivs, int(subdivisions/2))] = random.randint(0, 1)
            # Set bass line
            note_map[5, ] = np.repeat([1, 0, 1, 0], subdivs/4)
            # set intensity category
            intensity_cat = 3
            # Harmonic Minor
            scale = 5
            key_notes = key + scales[scale]
    elif intensity < 15:
        chord_root = chord_priority[random.randint(0, 6)]
        if intensity_cat != 4:
            # turn on/off hi hats
            note_map[2, ] = np.repeat(random.randint(0, 1), subdivs)
            # randomly distribute kicks
            note_map[0, range(0, subdivs, int(subdivisions/2))] = random.randint(0, 1)
            octave = 2
            # Set bass line
            note_map[5, ] = np.repeat(1, subdivs)
            clear_channels()
            intensity_cat = 4
            # Altered Scale
            scale = 6
            key_notes = key + scales[scale]
    else:
        chord_root = chord_priority[random.randint(0, 6)]
        if sdiv % 2 == 0:
            send_pads(1)
        if intensity_cat != 5:
            # turn on/off hi hats
            note_map[2, ] = np.repeat(1, subdivs)
            # randomly distribute kicks
            note_map[0, ] = np.array([1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0])
            octave = 3
            clear_channels()
            intensity_cat = 5
            # Diminished Scale
            scale = 7
            key_notes = key + scales[scale]
        if index > subdivs * 16 and not resolved:
            key_change("C", 0)
            resolved = True
            # Turn off snares
            note_map[1, ] = np.repeat(0, subdivs)


while True:
    sleep_time = max([0, (bpm - offset)])
    time.sleep(sleep_time)

    # start timer
    t0 = time.time()

    if counter >= subdivs:
        counter = 0
    if counter % subdiv_level[intensity] == 0:
        update_note_map(counter, index_counter)

    # Kick Drum
    if note_map[0, counter] == 1:
        send_drums(36)

    # Snare Drum
    if note_map[1, counter] == 1:
        send_drums(38)

    # Hi Hats
    if note_map[2, counter] == 1:
        send_drums(42)

    # Chords
    if note_map[3, counter] == 1:
        play_chords(True, chord_root)
    elif note_map[3, counter] == -1:
        play_chords(False, chord_root)

    # Lead Melody
    if note_map[4, counter] == 1:
        play_lead(True, key_notes[melody_note])
    elif note_map[4, counter] == -1:
        play_lead(False, key_notes[melody_note])

    # Bass
    if note_map[5, counter] == 1:
        send_bass(key_notes[chord_root])

    t1 = time.time()

    offset = t1 - t0
    counter = counter + 1
    index_counter = index_counter + 1


clear_channels()

midiout.close_port()
