#!/usr/bin/env python
from __future__ import unicode_literals, print_function
from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
import argparse
import ffmpeg
import logging
import sys


logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)


parser = argparse.ArgumentParser(description='Convert speech audio to text using Google Speech API')
parser.add_argument('in_filename', help='Input filename (`-` for stdin)')


def decode_audio(in_filename, **input_kwargs):
    try:
        out, err = (ffmpeg
            .input(in_filename, **input_kwargs)
            .output('-', format='s16le', acodec='pcm_s16le', ac=1, ar='16k')
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        print(e.stderr, file=sys.stderr)
        sys.exit(1)
    return out


def get_transcripts(audio_data):
    client = speech.SpeechClient()
    audio = types.RecognitionAudio(content=audio_data)
    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code='en-US'
    )
    response = client.recognize(config, audio)
    return [result.alternatives[0].transcript for result in response.results]


def transcribe(in_filename):
    audio_data = decode_audio(in_filename)
    transcripts = get_transcripts(audio_data)
    for transcript in transcripts:
        print(repr(transcript.encode('utf-8')))


if __name__ == '__main__':
    args = parser.parse_args()
    transcribe(args.in_filename)
