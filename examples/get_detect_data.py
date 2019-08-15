#!/usr/bin/env python
"""
Retrieve and process all the external data for hardware detection.
"""

import sys
import collections
import math
import json

import requests
import pandas

from ffmpeg import _detect

PLATFORM_TO_PY = {
    'Apple': 'Darwin',
}

HWACCELINTRO_URL = 'https://trac.ffmpeg.org/wiki/HWAccelIntro'
API_TO_HWACCEL = {
    'AMF': 'amf',
    'NVENC/NVDEC/CUVID': 'cuvid',
    'Direct3D 11': 'd3d11va',
    'Direct3D 9 (DXVA2)': 'dxva2',
    'libmfx': 'libmfx',
    'MediaCodec': 'mediacodec',
    'Media Foundation': 'mediafoundation',
    'MMAL': 'mmal',
    'OpenCL': 'opencl',
    'OpenMAX': 'omx',
    'V4L2 M2M': 'v4l2m2m',
    'VAAPI': 'vaapi',
    'VDPAU': 'vdpau',
    'VideoToolbox': 'videotoolbox',
}

NVIDIA_GPU_MATRIX_URL = (
    'https://developer.nvidia.com/video-encode-decode-gpu-support-matrix')
NVIDIA_LINE_SUFFIXES = {'geforce': ['gtx titan', 'gtx', 'gt', 'rtx']}
NVIDIA_CODEC_COLUMN_PREFIXES = {
    'mpeg-1': 'mpeg1video', 'mpeg-2': 'mpeg2video',
    'vc-1': 'vc1',
    'vp8': 'vp8', 'vp9': 'vp9',
    'h.264': 'h264', 'h.265': 'hevc'}


def get_hwaccel_data():
    """
    Download the ffmpeg hwaccel API support matrix to detection data.
    """
    response = requests.get(HWACCELINTRO_URL)
    api_avail_table, impl_table = pandas.read_html(response.content)

    gpu_vendor_cols = api_avail_table.loc[1][1:]
    platform_cols = api_avail_table.loc[0][1:]
    api_rows = api_avail_table[0][2:]

    hwaccels = collections.OrderedDict()
    hwaccels['api_avail'] = platforms = collections.OrderedDict()
    for gpu_vendor_idx, gpu_vendor in enumerate(gpu_vendor_cols):
        platform = platform_cols[gpu_vendor_idx + 1]
        platform = PLATFORM_TO_PY.get(platform, platform)
        gpu_vendors = platforms.setdefault(platform, collections.OrderedDict())
        avail_hwaccels = gpu_vendors.setdefault(gpu_vendor, [])
        for api_idx, api in enumerate(api_rows):
            if api_avail_table[gpu_vendor_idx + 1][api_idx + 2] != 'N':
                avail_hwaccels.append(API_TO_HWACCEL[api])

    return hwaccels


def get_nvidia_data():
    """
    Download the NVIDIA GPU support matrix to detection data.
    """
    response = requests.get(NVIDIA_GPU_MATRIX_URL)
    tables = pandas.read_html(response.content)
    (
        nvenc_recent, nvenc_consumer, nvenc_workstation, nvenc_virt,
        nvdec_recent, nvdec_consumer, nvdec_workstation, nvdec_virt) = tables
    nv_coders = dict(
        encoders=(
            nvenc_recent, nvenc_consumer, nvenc_workstation, nvenc_virt),
        decoders=(
            nvdec_recent, nvdec_consumer, nvdec_workstation, nvdec_virt))
    nvidia = collections.OrderedDict(lines=[])

    # Compile aggregate data needed to parse individual rows
    for nv_coder_table in tables:
        for board in nv_coder_table['BOARD']:
            if board == 'BOARD':
                continue
            line = board.replace('\xa0', ' ').split(None, 1)[0].lower()
            if line not in nvidia['lines']:
                nvidia['lines'].append(line)
    for line, line_suffixes in NVIDIA_LINE_SUFFIXES.items():
        for line_suffix in reversed(line_suffixes):
            nvidia['lines'].insert(0, ' '.join((line, line_suffix)))

    for coder_type, nv_coder_tables in nv_coders.items():
        coder_data = nvidia[coder_type] = collections.OrderedDict(
            model_lines=collections.OrderedDict(),
            boards=collections.OrderedDict())
        for nv_coder_table in nv_coder_tables:
            for nv_coder_row_idx, nv_coder_row in nv_coder_table.iterrows():
                nv_coder_row_values = {
                    idx: cell for idx, cell in enumerate(nv_coder_row[1:]) if (
                        cell and
                        not (isinstance(cell, float) and math.isnan(cell)))}
                if not nv_coder_row_values:
                    # Divider row
                    continue

                # Assemble the data for this row to use for each model or range
                model_data = collections.OrderedDict()
                for key, value in nv_coder_row.items():
                    if isinstance(key, tuple):
                        if key[0] == key[1]:
                            key = key[0]
                        else:
                            key = ' '.join(key)
                    if value in {'YES', 'NO'}:
                        model_data[key] = value == 'YES'
                    else:
                        model_data[key] = value
                model_data['BOARD'] = model_data['BOARD'].replace('\xa0', ' ')
                # Add keys for the ffmpeg codec names for fast lookup
                for codec_prefix, codec in (
                        NVIDIA_CODEC_COLUMN_PREFIXES.items()):
                    for column_idx, column in enumerate(nv_coder_row.keys()):
                        if isinstance(column, tuple):
                            if column[0] == column[1]:
                                column = column[0]
                            else:
                                column = ' '.join(column)
                        if column.lower().startswith(codec_prefix):
                            model_data[codec] = nv_coder_row[
                                column_idx] == 'YES'
                            break
                    else:
                        # Assume encoder support is not available
                        model_data[codec] = False

                coder_data['boards'][model_data['BOARD']] = model_data

                _detect._parse_models(
                    model_lines=nvidia['lines'],
                    boards=model_data['BOARD'].lower(),
                    model_data=model_data['BOARD'],
                    model_lines_data=coder_data['model_lines'])

        # Cleanup any deviations from the convention where models from
        # multiple lines are in the same BOARD cell
        for model_line, model_line_data in coder_data['model_lines'].items():
            for line, line_suffixes in NVIDIA_LINE_SUFFIXES.items():
                if not model_line.startswith(line):
                    continue
                for model_num, boards in list(
                        model_line_data['models'].items()):
                    for line_suffix in line_suffixes:
                        if not model_num.startswith(line_suffix + ' '):
                            continue
                        coder_data['model_lines'][
                            ' '.join((line, line_suffix))]['models'][
                                model_num[len(line_suffix + ' '):]
                            ] = model_line_data['models'].pop(model_num)
        # Clean up some annoying clashes between the titan model line and
        # GeForce GTX model numbers
        del coder_data['model_lines']['geforce gtx titan']['models']['']
        coder_data['model_lines']['geforce gtx titan']['models'][
            'xp'] = coder_data['model_lines']['titan']['models'].pop('xp')
        coder_data['model_lines']['geforce gtx titan']['models'][
            'black'] = titan_black = coder_data['model_lines'][
                'titan']['models'].pop('black')
        coder_data['model_lines']['geforce gtx']['models'][
            'titan'] = titan_black

    return nvidia


def main():
    """
    Download ffmpeg detection data.
    """
    data = collections.OrderedDict(
        hwaccels=get_hwaccel_data(),
        nvidia=get_nvidia_data(),
    )
    json.dump(data, sys.stdout, indent=2)


if __name__ == '__main__':
    main()
