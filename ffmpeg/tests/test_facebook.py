from __future__ import unicode_literals

import os
import random
import re
import subprocess
from builtins import bytes, range, str

import ffmpeg
import pytest
from ffmpeg import nodes

try:
    import mock  # python 2
except ImportError:
    from unittest import mock  # python 3


def pip_to_rtmp(url):
    """ Capture Facetime camera and screen in macOS and stream it to facebook
    """
    facetime_camera_input = (
        ffmpeg
        .input('FaceTime:1', format='avfoundation', pix_fmt='uyvy422', framerate=30, s='320x240', probesize='200M')
    )

    audio = facetime_camera_input.audio

    # ffmpeg in MacOS AVFoundation MUST increase the thread_queue_size in order to handle PIP
    video = (
        ffmpeg
        .header(thread_queue_size='512', vsync='2')
        .input('1:1', format='avfoundation',
               pix_fmt='uyvy422', framerate=30, probesize='200M')
        .overlay(facetime_camera_input)

    )
    output = (
        ffmpeg
        .output(video, audio, url, vsync='2', s='1280x720', pix_fmt='yuv420p', video_bitrate='1500000', f='flv',
                vcodec='libx264', preset='fast', x264opts='keyint=15', g='30', ac='2', ar='48000', acodec="aac", audio_bitrate="128000")
    )

    return output.overwrite_output().compile()


def test_rtmp():
    expected_result = ['ffmpeg', '-thread_queue_size', '512', '-vsync', '2', '-f', 'avfoundation', '-framerate', '30', '-pix_fmt', 'uyvy422', '-probesize', '200M', '-i', '1:1', '-f', 'avfoundation', '-framerate', '30', '-pix_fmt', 'uyvy422', '-probesize', '200M', '-s', '320x240', '-i', 'FaceTime:1', '-filter_complex', '[0][1]overlay=eof_action=repeat[s0]',
                       '-map', '[s0]', '-map', '1:a', '-f', 'flv', '-b:v', '1500000', '-b:a', '128000', '-ac', '2', '-acodec', 'aac', '-ar', '48000', '-g', '30', '-pix_fmt', 'yuv420p', '-preset', 'fast', '-s', '1280x720', '-vcodec', 'libx264', '-vsync', '2', '-x264opts', 'keyint=15', 'rtmps://live-api-s.facebook.com:443/rtmp/input_your_facebook_stream_key_here', '-y']
    # Your facebook key should look like: 123456789012345?s_bl=1&s_ps=1&s_sml=1&s_sw=0&s_vt=api-s&a=AbCdEfGhiJK12345
    your_facebook_key = 'input_your_facebook_stream_key_here'
    facebook_stream_url = 'rtmps://live-api-s.facebook.com:443/rtmp/{}'.format(your_facebook_key)
    result = pip_to_rtmp(facebook_stream_url)
    assert result == expected_result
