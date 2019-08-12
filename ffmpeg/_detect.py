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
import collections
import re
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

# Separators to divide a range of models within a line
MODEL_RANGE_SEPARATORS = ['-', '>']

HWACCEL = dict(
    # List `hwaccel` options by order of expected performance when available.
    BY_PERFORMANCE=[
        # NVidia
        'nvdec', 'cuvid', 'cuda',
        # AMD
        'amf',
        # Windows
        'qsv', 'd3d11va', 'dxva2',
        # Linux
        'vaapi', 'vdpau', 'drm'],
    OUTPUT_FORMATS={
        'nvdec': 'cuda',
        'vaapi': 'vaapi'})

GPU = dict(
    PRODUCT_RE=re.compile(r'(?P<chip>[^[]+)(\[(?P<board>[^]]+)\]|)'),
    WMI_PROPERTIES=collections.OrderedDict(
        vendor='AdapterCompatibility', board='VideoProcessor'))

# Loaded from JSON
DATA = None


def detect_gpus():
    """
    Detect the vendor, generation and model for each GPU if possible.
    """
    plat_sys = platform.system()
    gpus = []

    if plat_sys == 'Linux':
        # TODO: Android and other Linux'es that don't have `lshw`
        display_output = subprocess.check_output(
            ['lshw', '-class', 'display', '-json'], universal_newlines=True)
        displays_data = json.loads(
            display_output.strip().strip(','),
            object_pairs_hook=collections.OrderedDict)
        if not isinstance(displays_data, list):
            # TODO: Confirm this is how `lshw` handles multiple GPUs
            displays_data = [displays_data]
        for display_data in displays_data:
            gpu = collections.OrderedDict(
                vendor=display_data['vendor'].replace(' Corporation', ''))
            # TODO get multiple GPUs from lshw
            gpus.append(gpu)

            product_match = GPU['PRODUCT_RE'].search(display_data['product'])
            if product_match:
                gpu.update(**product_match.groupdict())
                if not gpu['board']:
                    gpu['board'] = gpu.pop('chip')

    elif plat_sys == 'Windows':
        import wmi
        for controller in wmi.WMI().Win32_VideoController():
            gpu = collections.OrderedDict()
            for key, wmi_prop in GPU['WMI_PROPERTIES'].items():
                value = controller.wmi_property(wmi_prop).value
                if value:
                    gpu[key] = value
            if gpu:
                gpus.append(gpu)

    else:
        # TODO Other platforms
        raise NotImplementedError(
            'GPU detection for {0!r} not supported yet'.format(plat_sys))

    if not gpus:
        raise ValueError('No GPUs detected')

    data = _get_data()
    for gpu in gpus:
        vendor_data = data.get(gpu.get('vendor', '').lower())
        if vendor_data:

            model_lines_data = _parse_models(
                model_lines=vendor_data['lines'],
                boards=gpu['board'].lower(), model_data={})
            gpu['model_line'] = list(model_lines_data.keys())[0]
            gpu['model_num'] = list(model_lines_data[
                gpu['model_line']]['models'].keys())[0]

            for coder_type in ['encoders', 'decoders']:
                model_line_data = vendor_data[coder_type]['model_lines'][
                    gpu['model_line']]
                coder_boards = model_line_data['models'].get(
                    gpu['model_num'])
                if coder_boards is None:
                    for model_range, boards in model_line_data[
                            'model_ranges']:
                        # TODO proper model range matching
                        if gpu['model_num'] in model_range:
                            coder_boards = boards
                            break
                if coder_boards is None:
                    continue
                gpu[coder_type] = vendor_data[coder_type]['boards'][
                    coder_boards]

    return gpus


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
    gpus = detect_gpus()
    api_avail = set()
    for gpu in gpus:
        vendor_apis = data['hwaccels']['api_avail'][plat_sys].get(
            gpu['vendor'])
        if vendor_apis:
            api_avail.update(vendor_apis)
    hwaccels = [
        hwaccel for hwaccel in hwaccels if hwaccel['name'] in api_avail]

    # Filter encoders and decoders based on what's supported by the GPU
    for gpu in gpus:
        for coder_type in ['encoders', 'decoders']:
            coder_data = gpu.get(coder_type)
            if coder_data is None:
                continue
            for hwaccel in hwaccels:
                for codec, coders in hwaccel.get('codecs', {}).items():
                    coder_supported = coder_data.get(codec)
                    if coder_supported is None or coder_supported:
                        # This encoder/decoder is supported, no need to filter
                        # it out
                        continue

                    # This codec isn't supported by the GPU hjardware
                    coders.pop(coder_type, None)

    hwaccels.sort(key=lambda hwaccel: (
        # Sort unranked hwaccels last, but in the order given by ffmpeg
        hwaccel['name'] in HWACCEL['BY_PERFORMANCE'] and 1 or 0,
        (
            # Sort ranked hwaccels per the constant
            hwaccel['name'] in HWACCEL['BY_PERFORMANCE'] and
            HWACCEL['BY_PERFORMANCE'].index(hwaccel['name']))))

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

    codecs_kwargs = []
    default_kwargs = collections.OrderedDict(
        output=collections.OrderedDict())
    if avail_encoders:
        default_kwargs['output']['codec'] = avail_encoders[0]
    for hwaccel in hwaccels_data['hwaccels']:

        if hwaccel['codecs']:
            # This hwaccel requires specific coders.
            for hwaccel_encoder in hwaccel['codecs'].get(
                    encoder, {}).get('encoders', []):
                # We have an accelerated encoder, include it.
                # Remove hwaccel codecs from future consideration.
                avail_encoders.remove(hwaccel_encoder)
                hwaccel_kwargs = collections.OrderedDict(
                    input=collections.OrderedDict(hwaccel=hwaccel['name']),
                    output=collections.OrderedDict(codec=hwaccel_encoder))
                if hwaccel['name'] in HWACCEL['OUTPUT_FORMATS']:
                    hwaccel_kwargs['input']['hwaccel_output_format'] = (
                        HWACCEL['OUTPUT_FORMATS'][hwaccel['name']])
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
            hwaccel_kwargs['input'] = collections.OrderedDict(
                hwaccel=hwaccel['name'])
            codecs_kwargs.append(hwaccel_kwargs)

    codecs_kwargs.append(default_kwargs)
    return codecs_kwargs


__all__ = [
    'detect_gpus',
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
            DATA = json.load(
                data_opened, object_pairs_hook=collections.OrderedDict)
    return DATA


def _parse_models(
        model_lines, boards, model_data,
        model_lines_data=None, model_line=None):
    """
    Parse model lines, sets and ranges from a boards string.
    """
    if model_lines_data is None:
        model_lines_data = collections.OrderedDict()

    boards = boards.strip().lower()
    model_line_positions = [
        (boards.index(next_model_line), idx, next_model_line)
        for idx, next_model_line in enumerate(model_lines)
        if next_model_line in boards]
    if model_line_positions:
        pos, idx, next_model_line = min(model_line_positions)
        model_group, next_boards = boards.split(next_model_line.lower(), 1)
    else:
        model_group = boards
        next_boards = ''

    model_group = model_group.strip()
    if model_group:
        # First item is a model range for the previous model line
        model_line_data = model_lines_data.setdefault(
            model_line, collections.OrderedDict(
                models=collections.OrderedDict(), model_ranges=[]))

        models = []
        for model_split in model_group.split('/'):
            models.extend(
                model.strip()
                for model in model_split.split('+'))

        for model_range in models:
            for model_range_separator in MODEL_RANGE_SEPARATORS:
                model_range_parameters = model_range.split(
                    model_range_separator)
                if len(model_range_parameters) > 1:
                    # This is a range of models
                    if model_range in model_line_data['model_ranges']:
                        model_line_data['model_ranges'][
                            model_line_data['model_ranges'].index(
                                model_range)] = model_data
                    else:
                        model_line_data['model_ranges'].append(
                            [model_range, model_data])
                    break
            else:
                model_line_data['models'][model_range] = model_data

    next_boards = next_boards.strip()
    if next_boards:
        return _parse_models(
            model_lines=model_lines, boards=next_boards,
            model_data=model_data, model_lines_data=model_lines_data,
            model_line=next_model_line)

    return model_lines_data


def main(args=None):
    """
    Dump all ffmpeg build data to json.
    """
    args = parser.parse_args(args)
    data = collections.OrderedDict(
        gpus=detect_gpus(),
        hwaccels=detect_hwaccels(cmd=args.ffmpeg),
        codecs=detect_codecs(cmd=args.ffmpeg))
    json.dump(data, sys.stdout, indent=2)


if __name__ == '__main__':
    main()
