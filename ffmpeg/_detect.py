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
import copy
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
    Order the available hardware accelerations by performance.
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


def detect_codecs(decoder, encoder, hwaccels=None, cmd='ffmpeg'):
    """
    Detect the optimal decoders and encoders on the optimal hwaccel.
    """
    hwaccels_data = detect_hwaccels(hwaccels, cmd=cmd)

    build_codecs = hwaccels_data['codecs']

    avail_decoders = build_codecs.get(decoder, {}).get('decoders', [])
    avail_encoders = build_codecs.get(encoder, {}).get('encoders', [])
    if not avail_decoders:
        raise ValueError(
            'Could not detect a supported decoder for {0!r}'.format(decoder))
    if not avail_encoders:
        raise ValueError(
            'Could not detect a supported encoder for {0!r}'.format(encoder))

    codecs_kwargs = []
    default_kwargs = dict(output=dict(codec=avail_encoders[0]))
    for hwaccel in hwaccels_data['hwaccels']:

        if hwaccel['codecs']:
            # This hwaccel requires specific coders.
            for hwaccel_encoder in hwaccel['codecs'].get(
                    encoder, {}).get('encoders', []):
                # We have an accelerated encoder, include it.
                # Remove hwaccel codecs from future consideration.
                hwaccel_encoder = hwaccel_encoder
                avail_encoders.remove(hwaccel_encoder)
                hwaccel_kwargs = dict(
                    input=dict(hwaccel=hwaccel['name']),
                    output=dict(codec=hwaccel_encoder))
                codecs_kwargs.append(hwaccel_kwargs)
                for hwaccel_decoder in hwaccel['codecs'].get(
                        decoder, {}).get('decoders', []):
                    if hwaccel_decoder in avail_decoders:
                        # We have an accelerated decoder, can make a minor but
                        # significant difference.
                        # Remove hwaccel codecs from future consideration.
                        hwaccel_kwargs['input']['codec'] = hwaccel_decoder
                        avail_decoders.remove(hwaccel_decoder)
                # Otherwise let ffmpeg choose the decoder

        else:
            # This hwaccel doesn't require specific coders.
            hwaccel_kwargs = copy.deepcopy(default_kwargs)
            hwaccel_kwargs['input'] = dict(hwaccel=hwaccel['name'])
            codecs_kwargs.append(hwaccel_kwargs)

    codecs_kwargs.append(default_kwargs)
    return codecs_kwargs


__all__ = [
    'detect_gpu',
    'detect_hwaccels',
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
