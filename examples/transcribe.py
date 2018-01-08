#!/usr/bin/env python
from __future__ import unicode_literals
import IPython

from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
from google.protobuf.json_format import MessageToJson
import argparse
import ffmpeg
import logging
import subprocess
import sys


logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)


parser = argparse.ArgumentParser(description='Convert speech audio to text using Google Speech API')
parser.add_argument('in_file', help='Input filename (`-` for stdin)')
parser.add_argument('--out-file', type=argparse.FileType('w'), default='-',
    help='Output filename (defaults to stdout)')
parser.add_argument('--json', action='store_true', help='Output raw JSON response')


def decode_audio(in_filename, **input_kwargs):
    p = subprocess.Popen(
        (ffmpeg
            .input(in_filename, **input_kwargs)
            .output('-', format='s16le', acodec='pcm_s16le', ac=1, ar='16k')
            .overwrite_output()
            .compile()
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    out = p.communicate()
    if p.returncode != 0:
        sys.stderr.write(out[1])
        sys.exit(1)
    return out[0]


def transcribe_data(audio_data):
    client = speech.SpeechClient()
    audio = types.RecognitionAudio(content=audio_data)
    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code='en-US'
    )
    return client.recognize(config, audio)


def transcribe(in_filename):
    audio_data = decode_audio(in_filename)
    return transcribe_data(audio_data)


def transcribe_to_file(in_filename, out_file=sys.stdout, as_json=False):
    transcription = transcribe(in_filename)
    if as_json:
        out_file.write(MessageToJson(transcription).encode('utf-8'))
    else:
        transcripts = [result.alternatives[0].transcript for result in transcription.results]
        for transcript in transcripts:
            line = transcript + '\n'
            out_file.write(line.encode('utf-8'))


if __name__ == '__main__':
    args = parser.parse_args()
    transcribe_to_file(args.in_file, args.out_file, as_json=args.json)
