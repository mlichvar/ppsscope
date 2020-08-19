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
import socket
import time

def scpi(sock, command):
    if debug:
        print('DEBUG: Sending {}'.format(command))
    sock.sendall((command + '\n').encode('ASCII'))

    if '?' not in command:
        return None

    msg = b''
    while True:
        r = sock.recv(4096)
        if debug:
            print('DEBUG: Received {} bytes ({})'.format(len(r), r[0:50]))
        if len(r) == 0:
            msg = ""
            break

        msg += r

        if msg[0:2] == b'#9':
            ilen = int(msg[2:11])
            if len(msg) >= 11 + ilen + 1:
                decoded_msg = msg[11:11 + ilen].hex()
                break
            # Work around a firmware bug
            if len(msg) == 12 and msg[11] == ord('\n'):
                decoded_msg = ""
                break
        else:
            if msg[-1] == ord('\n'):
                decoded_msg = msg.decode('ASCII').strip()
                break

    if debug:
        print('DEBUG: Decoded message {} bytes ({})'.format(len(decoded_msg), decoded_msg[0:50]))

    return decoded_msg

def trigger(s):
    scpi(s, ':SINGLE')
    scpi(s, '*WAI')
    waited = 0
    while scpi(s, ':TRIGGER:STATUS?') != 'STOP':
        time.sleep(0.05)
        waited += 0.05
    return waited

def main():
    parser = optparse.OptionParser(usage="Usage: %prog [OPTION]... SCOPE_ADDRESS")
    parser.add_option("-1", "--source1", dest="source1", type="int", default=1, help="set first source channel (default 1)")
    parser.add_option("-2", "--source2", dest="source2", type="int", default=2, help="set second source channel (default 2)")
    parser.add_option("-p", "--port", dest="port", type="int", default=5555, help="set port (default 5555)")
    parser.add_option("-d", "--debug", dest="debug", action="store_true", default=False, help="enable debug messages")

    (options, args) = parser.parse_args()

    host = args[0]
    port = options.port

    global debug
    debug = options.debug

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))

    idn = scpi(s, '*IDN?')
    print('IDN: {}'.format(idn))

    scpi(s, ':WAVEFORM:MODE RAW')
    scpi(s, ':STOP')
    scpi(s, '*WAI')
    trigger(s)
    time.sleep(1)

    scpi(s, ':WAVEFORM:FORMAT BYTE')

    scpi(s, ':WAVEFORM:SOURCE CHAN{}'.format(options.source1))
    preamble = scpi(s, ':WAVEFORM:PREAMBLE?').split(',')
    depth = int(preamble[2])

    print('DEPTH: {}'.format(depth))
    print('XINCREMENT: {}'.format(preamble[4]))
    print('XORIGIN: {}'.format(preamble[7]))
    print('XREFERENCE: {}'.format(preamble[6]))
    print('Y1INCREMENT: {}'.format(preamble[7]))
    print('Y1ORIGIN: {}'.format(preamble[8]))
    print('Y1REFERENCE: {}'.format(preamble[9]))

    scpi(s, ':WAVEFORM:SOURCE CHAN{}'.format(options.source2))
    preamble = scpi(s, ':WAVEFORM:PREAMBLE?').split(',')
    print('Y2INCREMENT: {}'.format(preamble[7]))
    print('Y2ORIGIN: {}'.format(preamble[8]))
    print('Y2REFERENCE: {}'.format(preamble[9]))

    scpi(s, ':WAVEFORM:START 1')
    scpi(s, ':WAVEFORM:STOP {}'.format(depth))
    channel_swap = 1

    while True:
        waited = trigger(s)

        print('TRIGGER: {:.1f} waited {:.2f}'.format(time.time(), waited))

        if True:
            # Minimize the number of switching between source channels
            # as it is a very slow command
            if channel_swap:
                wave2 = scpi(s, ':WAVEFORM:DATA?')
                scpi(s, ':WAVEFORM:SOURCE CHAN{}'.format(options.source1))
                wave1 = scpi(s, ':WAVEFORM:DATA?')
            else:
                wave1 = scpi(s, ':WAVEFORM:DATA?')
                scpi(s, ':WAVEFORM:SOURCE CHAN{}'.format(options.source2))
                wave2 = scpi(s, ':WAVEFORM:DATA?')
            channel_swap = not channel_swap

            print('WAVE1: {}'.format(wave1))
            print('WAVE2: {}'.format(wave2))

if __name__ == "__main__":
    main()
