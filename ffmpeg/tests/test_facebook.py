from __future__ import unicode_literals
from builtins import bytes
from builtins import range
from builtins import str
import ffmpeg
import os
import pytest
import random
import re
import subprocess

try:
    import mock  # python 2
except ImportError:
    from unittest import mock  # python 3

    def pip_to_facebook(stream_key: str):
        """ Capture Facetime camera and screen in macOS and stream it to facebook
        """
        facetime_camera_input = (
            ffmpeg
            .input('FaceTime:1', format='avfoundation', pix_fmt='uyvy422', framerate=30, s='320x240', probesize='200M')
        )

        audio = facetime_camera_input.audio

        video = (
            ffmpeg
            .header(thread_queue_size='512', vsync='2')
            .input('1:1', format='avfoundation',
                   pix_fmt='uyvy422', framerate=30, probesize='200M')
            .overlay(facetime_camera_input)

        )
        output = (
            ffmpeg
            .output(video, audio, 'rtmps://live-api-s.facebook.com:443/rtmp/{}'.format(stream_key), vsync='2', s='1280x720', pix_fmt='yuv420p', video_bitrate='1500000', f='flv',
                    vcodec='libx264', preset='superfast', x264opts='keyint=15', g='30', ac='2', ar='48000', acodec="aac", audio_bitrate="128000")
        )

        output.overwrite_output().run()


def test_fluent_equality():
    pip_to_facebook('351682605501180?s_bl=1&s_ps=1&s_sml=1&s_sw=0&s_vt=api-s&a=AbzMoYVOuxBYwxs7')
