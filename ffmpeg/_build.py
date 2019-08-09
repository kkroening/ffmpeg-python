"""
Extract details about the ffmpeg build.
"""

import sys
import re
import subprocess
import json
import logging
import argparse

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    '--ffmpeg', default='ffmpeg',
    help='The path to the ffmpeg execuatble')


VERSION_RE = re.compile(r' version (?P<version>[^ ]+) ')

MUXER_RE = re.compile(
    r'^ (?P<demuxing>[D ])(?P<muxing>[E ]) '
    r'(?P<name>[^ ]+) +(?P<description>.+)$',
    re.M)
MUXER_FLAGS = dict(demuxing='D', muxing='E')

CODEC_RE = re.compile(
    r'^ (?P<decoding>[D.])(?P<encoding>[E.])'
    r'(?P<stream>[VAS.])(?P<intra_frame>[I.])'
    r'(?P<lossy>[L.])(?P<lossless>[S.]) '
    r'(?P<name>[^ ]+) +(?P<description>.+)$',
    re.M)
CODEC_FLAGS = dict(
    decoding='D', encoding='E',
    stream=dict(video='V', audio='A', subtitle='S'),
    intra_frame='I', lossy='L', lossless='S')
CODEC_DESCRIPTION_RE = re.compile(
    r'^(?P<description>.+?) \((de|en)coders: [^)]+ \)')
CODEC_CODERS_RE = re.compile(
    r' \((?P<type>(de|en)coders): (?P<coders>[^)]+) \)')

FILTER_RE = re.compile(
    r'^ (?P<timeline>[T.])(?P<slice>[S.])(?P<command>[C.]) '
    r'(?P<name>[^ ]+) +(?P<io>[^ ]+) +(?P<description>.+)$',
    re.M)
FILTER_FLAGS = dict(timeline='T', slice='S', command='C')

PIX_FMT_RE = re.compile(
    r'^(?P<input>[I.])(?P<output>[O.])(?P<accelerated>[H.])'
    r'(?P<palleted>[P.])(?P<bitstream>[B.]) '
    r'(?P<name>[^ ]+) +(?P<components>[0-9]+) +(?P<bits>[0-9]+)$',
    re.M)
PIX_FMT_FLAGS = dict(
    input='I', output='O', accelerated='H', palleted='P', bitstream='B')
PIX_FMT_INT_FIELDS = {'components', 'bits'}


def _run(args):
    """
    Run the command and return stdout but only print stderr on failure.
    """
    process = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        logger.error(stderr.decode())
        raise subprocess.CalledProcessError(
            process.returncode, process.args, output=stdout, stderr=stderr)
    return stdout.decode()


def _get_line_fields(
        stdout, header_lines, line_re, flags={}, int_fields=set()):
    """
    Extract field values from a line using the regular expression.
    """
    non_fields = set(flags).union({'name'})
    lines = stdout.split('\n', header_lines)[header_lines]
    data = {}
    for match in line_re.finditer(lines):
        groupdict = match.groupdict()

        data[match.group('name')] = fields = {
            key: key in int_fields and int(value) or value
            for key, value in groupdict.items()
            if key not in non_fields}

        if flags:
            fields['flags'] = {}
            for key, flag in flags.items():
                if isinstance(flag, dict):
                    fields['flags'][key] = groupdict[key]
                    for sub_key, sub_flag in flag.items():
                        fields['flags'][sub_key] = groupdict[key] == sub_flag
                else:
                    fields['flags'][key] = groupdict[key] == flag

    return data


def get_version(cmd='ffmpeg'):
    """
    Extract the version of the ffmpeg build.
    """
    stdout = _run([cmd, '-version'])
    match = VERSION_RE.search(stdout.split('\n')[0])
    return match.group('version')


def get_formats(cmd='ffmpeg'):
    """
    Extract the formats of the ffmpeg build.
    """
    stdout = _run([cmd, '-formats'])
    return _get_line_fields(stdout, 4, MUXER_RE, MUXER_FLAGS)


def get_demuxers(cmd='ffmpeg'):
    """
    Extract the demuxers of the ffmpeg build.
    """
    stdout = _run([cmd, '-demuxers'])
    return _get_line_fields(stdout, 4, MUXER_RE, MUXER_FLAGS)


def get_muxers(cmd='ffmpeg'):
    """
    Extract the muxers of the ffmpeg build.
    """
    stdout = _run([cmd, '-muxers'])
    return _get_line_fields(stdout, 4, MUXER_RE, MUXER_FLAGS)


def get_codecs(cmd='ffmpeg'):
    """
    Extract the codecs of the ffmpeg build.
    """
    stdout = _run([cmd, '-codecs'])
    codecs = _get_line_fields(stdout, 10, CODEC_RE, CODEC_FLAGS)
    for codec in codecs.values():
        for coders_match in CODEC_CODERS_RE.finditer(codec['description']):
            coders = coders_match.group(3).split()
            if coders:
                codec[coders_match.group(1)] = coders
        description_match = CODEC_DESCRIPTION_RE.search(codec['description'])
        if description_match is not None:
            codec['description'] = description_match.group('description')
    return codecs


def get_bsfs(cmd='ffmpeg'):
    """
    Extract the bsfs of the ffmpeg build.
    """
    stdout = _run([cmd, '-bsfs'])
    return stdout.split('\n')[1:-2]


def get_protocols(cmd='ffmpeg'):
    """
    Extract the protocols of the ffmpeg build.
    """
    stdout = [
        line.strip() for line in
        _run([cmd, '-protocols']).split('\n')]
    input_idx = stdout.index('Input:')
    output_idx = stdout.index('Output:')
    return dict(
        input=stdout[input_idx + 1:output_idx],
        output=stdout[output_idx + 1:-1])


def get_filters(cmd='ffmpeg'):
    """
    Extract the filters of the ffmpeg build.
    """
    stdout = _run([cmd, '-filters'])
    return _get_line_fields(stdout, 8, FILTER_RE, FILTER_FLAGS)


def get_pix_fmts(cmd='ffmpeg'):
    """
    Extract the pix_fmts of the ffmpeg build.
    """
    stdout = _run([cmd, '-pix_fmts'])
    return _get_line_fields(
        stdout, 8, PIX_FMT_RE, PIX_FMT_FLAGS, PIX_FMT_INT_FIELDS)


def get_sample_fmts(cmd='ffmpeg'):
    """
    Extract the sample_fmts of the ffmpeg build.
    """
    stdout = _run([cmd, '-sample_fmts'])
    fmts = {}
    for line in stdout.split('\n')[1:-1]:
        name, depth = line.split()
        fmts[name] = int(depth)
    return fmts


def get_layouts(cmd='ffmpeg'):
    """
    Extract the layouts of the ffmpeg build.
    """
    stdout = _run([cmd, '-layouts']).split('\n')
    channels_idx = stdout.index('Individual channels:')
    layouts_idx = stdout.index('Standard channel layouts:')
    data = {}

    data['channels'] = channels = {}
    for line in stdout[channels_idx + 2:layouts_idx - 1]:
        name, description = line.split(None, 1)
        channels[name] = description

    data['layouts'] = layouts = {}
    for line in stdout[layouts_idx + 2:-1]:
        name, decomposition = line.split(None, 1)
        layouts[name] = decomposition.split('+')

    return data


def get_colors(cmd='ffmpeg'):
    """
    Extract the colors of the ffmpeg build.
    """
    stdout = _run([cmd, '-colors'])
    return dict(line.split() for line in stdout.split('\n')[1:-1])


def get_devices(cmd='ffmpeg'):
    """
    Extract the devices of the ffmpeg build.
    """
    stdout = _run([cmd, '-devices'])
    return _get_line_fields(stdout, 4, MUXER_RE, MUXER_FLAGS)


def get_hw_devices(cmd='ffmpeg'):
    """
    Extract the hardware devices of the ffmpeg build.
    """
    stdout = _run([cmd, '-init_hw_device', 'list'])
    return stdout.split('\n')[1:-2]


def get_hwaccels(cmd='ffmpeg'):
    """
    Extract the hwaccels of the ffmpeg build.
    """
    stdout = _run([cmd, '-hwaccels'])
    return stdout.split('\n')[1:-2]


def get_build_data(cmd='ffmpeg'):
    """
    Extract details about the ffmpeg build.
    """
    return dict(
        version=get_version(cmd=cmd),
        formats=get_formats(cmd=cmd),
        demuxers=get_demuxers(cmd=cmd),
        muxers=get_muxers(cmd=cmd),
        codecs=get_codecs(cmd=cmd),
        bsfs=get_bsfs(cmd=cmd),
        protocols=get_protocols(cmd=cmd),
        filters=get_filters(cmd=cmd),
        pix_fmts=get_pix_fmts(cmd=cmd),
        sample_fmts=get_sample_fmts(cmd=cmd),
        layouts=get_layouts(cmd=cmd),
        colors=get_colors(cmd=cmd),
        devices=get_devices(cmd=cmd),
        hw_devices=get_hw_devices(cmd=cmd),
        hwaccels=get_hwaccels(cmd=cmd))

__all__ = [
    'get_build_data',
    'get_version',
    'get_version',
    'get_formats',
    'get_demuxers',
    'get_muxers',
    'get_codecs',
    'get_bsfs',
    'get_protocols',
    'get_filters',
    'get_pix_fmts',
    'get_sample_fmts',
    'get_layouts',
    'get_colors',
    'get_devices',
    'get_hw_devices',
    'get_hwaccels',
]


def main(args=None):
    """
    Dump all ffmpeg build data to json.
    """
    args = parser.parse_args(args)
    data = get_build_data(args.ffmpeg)
    json.dump(data, sys.stdout, indent=2)


if __name__ == '__main__':
    main()