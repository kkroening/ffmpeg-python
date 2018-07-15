#!/usr/bin/env python
from __future__ import unicode_literals, print_function
import argparse
import ffmpeg
import sys


parser = argparse.ArgumentParser(description='Generate video thumbnail')
parser.add_argument('in_filename', help='Input filename')
parser.add_argument('out_filename', help='Output filename')
parser.add_argument(
    '--time', type=int, default=0.1, help='Time offset')
parser.add_argument(
    '--width', type=int, default=120,
    help='Width of output thumbnail (height automatically determined by aspect ratio)')


def generate_thumbnail(in_filename, out_filename, time, width):
    try:
        (
            ffmpeg
            .input(in_filename, ss=time)
            .filter('scale', width, -1)
            .output(out_filename, vframes=1)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        print(e.stderr.decode(), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    args = parser.parse_args()
    generate_thumbnail(args.in_filename, args.out_filename, args.time, args.width)
