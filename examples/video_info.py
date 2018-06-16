#!/usr/bin/env python
from __future__ import unicode_literals, print_function
import argparse
import ffmpeg
import sys


parser = argparse.ArgumentParser(description='Get video information')
parser.add_argument('in_filename', help='Input filename')


if __name__ == '__main__':
    args = parser.parse_args()

    try:
        probe = ffmpeg.probe(args.in_filename)
    except ffmpeg.Error as e:
        print(e.stderr, file=sys.stderr)
        sys.exit(1)

    video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
    if video_stream is None:
        print('No video stream found', file=sys.stderr)
        sys.exit(1)

    width = int(video_stream['width'])
    height = int(video_stream['height'])
    num_frames = int(video_stream['nb_frames'])
    print('width: {}'.format(width))
    print('height: {}'.format(height))
    print('num_frames: {}'.format(num_frames))
