#!/usr/bin/python3
#
# Copyright (C) 2020  Miroslav Lichvar <mlichvar0@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import optparse
import sys
import time

def parse_waveform(yinc, yorig, yref, s):
    return [float((int(b) - yorig - yref) * yinc) for b in bytes.fromhex(s)]

def get_edges(waveform, level):
    edges = []
    for i in range(len(waveform) - 1):
        if waveform[i] <= level and waveform[i + 1] > level:
            sub = (level - waveform[i]) / (waveform[i + 1] - waveform[i])
            edges.append(i + sub)
    return edges

def main():
    parser = optparse.OptionParser(usage="Usage: %prog [OPTION]... < pps.capture")
    parser.add_option("-1", "--level1", dest="level1", type="float", default=1.0, help="set edge detection voltage for first channel (default 1.0V)")
    parser.add_option("-2", "--level2", dest="level2", type="float", default=1.0, help="set edge detection voltage for second channel (default 1.0V)")
    parser.add_option("-o", "--output", dest="output", default="", help="save offsets to file")

    (options, args) = parser.parse_args()

    last_ts = None
    triggers = 0
    timestamps = []
    offsets = []

    for line in sys.stdin:
        words = line.strip().split(" ")

        if words[0] in ("DEBUG:", "IDN:"):
            continue
        elif words[0] == "DEPTH:":
            depth = int(words[1])
            continue
        elif words[0] == "XINCREMENT:":
            xinc = float(words[1])
            continue
        elif words[0] == "XORIGIN:":
            xorig = float(words[1])
            continue
        elif words[0] == "XREFERENCE:":
            xref = float(words[1])
            continue
        elif words[0] == "Y1INCREMENT:":
            y1inc = float(words[1])
            continue
        elif words[0] == "Y1ORIGIN:":
            y1orig = float(words[1])
            continue
        elif words[0] == "Y1REFERENCE:":
            y1ref = float(words[1])
            continue
        elif words[0] == "Y2INCREMENT:":
            y2inc = float(words[1])
            continue
        elif words[0] == "Y2ORIGIN:":
            y2orig = float(words[1])
            continue
        elif words[0] == "Y2REFERENCE:":
            y2ref = float(words[1])
            continue
        elif words[0] == "TRIGGER:":
            ts = float(words[1])
            wave1 = wave2 = None
            triggers += 1
            continue
        elif words[0] == "WAVE1:":
            if len(words) > 1:
                wave1 = parse_waveform(y1inc, y1orig, y1ref, words[1])
            continue
        elif words[0] == "WAVE2:":
            if len(words) > 1:
                wave2 = parse_waveform(y2inc, y2orig, y2ref, words[1])
        else:
            print("unknown data {}".format(words[0]))
            continue

        if ts == None:
            print("Missing trigger timestamp after trigger #{}".format(triggers))
            continue

        if last_ts is not None and ts - last_ts > 1.5:
            print("Missing trigger between {} and {}".format(last_ts, ts))

        if last_ts is not None and ts - last_ts < 0.5:
            print("Extra trigger at {} trigger #{}".format(ts, triggers))

        if wave1 is None or wave2 is None:
            print("Missing waveform at {} trigger #{}".format(ts, triggers))
            ts = wave1 = wave2 = None
            continue

        if len(wave1) != depth or len(wave2) != depth:
            print("Short waveform at {} trigger #{}".format(ts, triggers))
            ts = wave1 = wave2 = None
            continue

        edges1 = get_edges(wave1, options.level1)
        edges2 = get_edges(wave2, options.level2)

        if len(edges1) < 1 or len(edges2) < 1:
            print("Missing edge at {} trigger #{}".format(ts, triggers))
            ts = wave1 = wave2 = None
            continue

        if len(edges1) > 1 or len(edges2) > 1:
            print("Too many edges at {} trigger #{}".format(ts, triggers))
            ts = wave1 = wave2 = None
            continue

        timestamps.append(ts)
        offsets.append(xinc * (edges2[0] - edges1[0]))

        last_ts = ts
        ts = wave1 = wave2 = None

    if len(offsets) < 2:
        print("Not enough offsets for statistics")
        return

    mean = sum(offsets) / len(offsets)
    minimum = min(offsets)
    maximum = max(offsets)
    stddev = (sum([(o - mean) * (o - mean) for o in offsets]) / (len(offsets) - 1))**0.5

    print("Samples: {:9}".format(len(offsets)))
    print("Resolution:{:7.1f} ns".format(1e9 * xinc))
    print("Mean:    {:+9.1f} ns".format(1e9 * mean))
    print("Min:     {:+9.1f} ns".format(1e9 * minimum))
    print("Max:     {:+9.1f} ns".format(1e9 * maximum))
    print("StdDev:  {:9.1f} ns".format(1e9 * stddev))

    if options.output:
        with open(options.output, "w") as f:
            for ts, o in zip(timestamps, offsets):
                f.write("{} {:+.1f}\n".format(ts, 1e9 * o))

if __name__ == "__main__":
    main()
