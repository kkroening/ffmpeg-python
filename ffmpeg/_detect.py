"""Detect optimal arguments for various options.

This module includes a number of constants used to attempt to detect the
options which will provide the best performance for a given OS/GPU/etc..

For most of these constants, it only matters that the best performing option
available for a given OS/platform/hardware rank first for that
OS/platform/hardware, not which OS/platform/hardware performs better.  For
example, it doesn't matter if `vdpau` is lower than `cuvid` or vice versa,
because one is only available for Linux and the other for Windows. Similarly,
it doesn't matter how `amf` is ranked with respect to `cuvid` because one is
only available on NVidia GPUs and the other AMD.  It *does* matter how
`cuvid`/`amf` are ranked with respect to `dxva2` because those could both be
available on the same OS and GPU.

Additions and suggestions for these constants are very much welcome,
especially if they come with benchmarks and/or good explanations from those
who understand this domain well.  Contributions of more complicated or
involved detection logic may also be welcome, though the case will have to be
made more rigorously.
"""

import sys
import platform
import os
import json
import logging
import argparse
import subprocess

import ffmpeg

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    '--ffmpeg', default='ffmpeg',
    help='The path to the ffmpeg execuatble')

# List `hwaccel` options by order of expected performance when available.
HWACCELS_BY_PERFORMANCE = [
    'cuvid', 'amf', 'vdpau',
    'qsv', 'd3d11va', 'dxva2', 'vaapi', 'drm']
# Loaded from JSON
DATA = None


def detect_gpu():
    """
    Detect the GPU vendor, generation and model if possible.
    """
    plat_sys = platform.system()
    if plat_sys == 'Linux':
        # TODO: Android and other Linux'es that don't have `lshw`
        display_output = subprocess.check_output(
            ['lshw', '-class', 'display', '-json'])
        return json.loads(display_output.decode().strip().strip(','))
    # TODO Other platforms


def detect_hwaccels(hwaccels=None, cmd='ffmpeg'):
    """
    Extract details about the ffmpeg build.
    """
    # Filter against what's available in the ffmpeg build
    hwaccels_data = ffmpeg.get_hwaccels(cmd=cmd)
    if hwaccels is None:
        # Consider all the available hwaccels
        hwaccels = hwaccels_data['hwaccels']
    else:
        # Support passing in a restricted set of hwaccels
        hwaccels = [
            hwaccel for hwaccel in hwaccels_data['hwaccels']
            if hwaccel['name'] in hwaccels]

    # Filter against which APIs are available on this OS+GPU
    data = _get_data()
    plat_sys = platform.system()
    gpu = detect_gpu()
    api_avail = data['hwaccels']['api_avail'][plat_sys][
        gpu['vendor'].replace(' Corporation', '')]
    hwaccels = [
        hwaccel for hwaccel in hwaccels if hwaccel['name'] in api_avail]

    hwaccels.sort(key=lambda hwaccel: (
        # Sort unranked hwaccels last, but in the order given by ffmpeg
        hwaccel['name'] in HWACCELS_BY_PERFORMANCE and 1 or 0,
        (
            # Sort ranked hwaccels per the constant
            hwaccel['name'] in HWACCELS_BY_PERFORMANCE and
            HWACCELS_BY_PERFORMANCE.index(hwaccel['name']))))
    hwaccels_data['hwaccels'] = hwaccels
    return hwaccels_data


def detect_coder(
        codec, coder, hwaccels=None, avail_codecs=None, cmd='ffmpeg'):
    """
    Determine the optimal decoder/encoder given the hwaccels.
    """
    if hwaccels is None:
        hwaccels = detect_hwaccels(cmd=cmd)
    if avail_codecs is None:
        avail_codecs = ffmpeg.get_codecs(cmd=cmd)[codec][coder]

    # Some accelerated codecs use a different prefix than the base codec
    base_codec = CODEC_SYNONYMS.get(codec, codec)

    # Gather all available accelerated coders for this codec
    codecs = []
    for hwaccel in hwaccels:
        hwaccel_codec = '{0}_{1}'.format(base_codec, hwaccel)
        if hwaccel_codec in avail_codecs:
            codecs.append(hwaccel_codec)

    codecs.append(codec)
    return codecs


def detect_codecs(
        decoder, encoder, hwaccels=None, avail_codecs=None, cmd='ffmpeg'):
    """
    Detect the optimal de/encoder for the codec based on the optimal hwaccel.
    """
    hwaccels = detect_hwaccels(hwaccels, cmd=cmd)

    build_codecs = ffmpeg.get_codecs(cmd=cmd)
    build_decoders = build_codecs[decoder]['decoders']
    build_encoders = build_codecs[encoder]['encoders']
    if avail_codecs is None:
        # Consider all the available hwaccels
        avail_codecs = dict(decoders=build_decoders, encoders=build_encoders)
    else:
        # Support passing in restricted sets of decoders and encoders
        avail_codecs['decoders'] = [
            codec for codec in avail_codecs['decoders']
            if codec in build_decoders]
        avail_codecs['encoders'] = [
            codec for codec in avail_codecs['encoders']
            if codec in build_encoders]

    return dict(
        hwaccels=hwaccels,
        decoders=detect_coder(
            decoder, 'decoders', hwaccels, avail_codecs['decoders']),
        encoders=detect_coder(
            encoder, 'encoders', hwaccels, avail_codecs['encoders']))


__all__ = [
    'detect_gpu',
    'detect_hwaccels',
    'detect_coder',
    'detect_codecs',
]


def _get_data():
    """
    Don't load the data JSON unless needed, cache in a global.
    """
    global DATA
    if DATA is None:
        with open(os.path.join(
                os.path.dirname(__file__), 'detect.json')) as data_opened:
            DATA = json.load(data_opened)
    return DATA


def main(args=None):
    """
    Dump all ffmpeg build data to json.
    """
    args = parser.parse_args(args)
    data = dict(
        gpu=detect_gpu(),
        hwaccels=detect_hwaccels(cmd=args.ffmpeg),
        codecs=detect_codecs(cmd=args.ffmpeg))
    json.dump(data, sys.stdout, indent=2)


if __name__ == '__main__':
    main()
