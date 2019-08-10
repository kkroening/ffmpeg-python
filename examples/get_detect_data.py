#!/usr/bin/env python
"""
Retrieve and process all the external data for hardware detection.
"""

import sys
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
NVIDIA_CODEC_COLUMN_PREFIXES = {'h.264': 'h264', 'h.265': 'hevc'}


def get_hwaccel_data():
    """
    Download the ffmpeg hwaccel API support matrix to detection data.
    """
    response = requests.get(HWACCELINTRO_URL)
    api_avail_table, impl_table = pandas.read_html(response.content)

    gpu_vendor_cols = api_avail_table.loc[1][1:]
    platform_cols = api_avail_table.loc[0][1:]
    api_rows = api_avail_table[0][2:]

    hwaccels = {}
    hwaccels['api_avail'] = platforms = {}
    for gpu_vendor_idx, gpu_vendor in enumerate(gpu_vendor_cols):
        platform = platform_cols[gpu_vendor_idx + 1]
        platform = PLATFORM_TO_PY.get(platform, platform)
        gpu_vendors = platforms.setdefault(platform, {})
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
    nvidia = dict(lines=[], model_lines={}, boards={})

    # Compile aggregate data needed to parse individual rows
    for nvenc_table in (
            nvenc_recent, nvenc_consumer, nvenc_workstation, nvenc_virt):
        for board in nvenc_table['BOARD']:
            line = board.replace('\xa0', ' ').split(None, 1)[0].lower()
            if line not in nvidia['lines']:
                nvidia['lines'].append(line)
    for line, line_suffixes in NVIDIA_LINE_SUFFIXES.items():
        for line_suffix in reversed(line_suffixes):
            nvidia['lines'].insert(0, ' '.join((line, line_suffix)))

    for nvenc_table in (
            nvenc_recent, nvenc_consumer, nvenc_workstation, nvenc_virt):
        for nvenc_row_idx, nvenc_row in nvenc_table.iterrows():
            nvenc_row_values = {
                idx: cell for idx, cell in enumerate(nvenc_row[1:]) if (
                    cell and
                    not (isinstance(cell, float) and math.isnan(cell)))}
            if not nvenc_row_values:
                # Divider row
                continue

            # Assemble the data for this row to use for each model or range
            model_data = {}
            for key, value in nvenc_row.items():
                if value in {'YES', 'NO'}:
                    model_data[key] = value == 'YES'
                else:
                    model_data[key] = value
            model_data['BOARD'] = model_data['BOARD'].replace(
                '\xa0', ' ')
            # Add keys for the data for the ffmpeg codec names for fast lookup
            for codec_prefix, codec in NVIDIA_CODEC_COLUMN_PREFIXES.items():
                for column_idx, column in enumerate(nvenc_row.keys()):
                    if column.lower().startswith(codec_prefix):
                        model_data[codec] = nvenc_row[column_idx] == 'YES'
                        break
            nvidia['boards'][model_data['BOARD']] = model_data

            _detect._parse_models(
                model_lines=nvidia['lines'],
                boards=model_data['BOARD'].lower(),
                model_data=model_data['BOARD'],
                model_lines_data=nvidia['model_lines'])

    # Clean up some annoying clashes between the titan model line and GeForce
    # GTX model numbers
    for model_line, model_line_suffixes in NVIDIA_LINE_SUFFIXES.items():
        models_data = nvidia['model_lines'][model_line]['models']
        for model_num in models_data:
            for model_line_suffix in model_line_suffixes:
                if model_num.startswith(model_line_suffix + ' '):
                    models_data[model_num[
                        len(model_line_suffix + ' '):]] = models_data.pop(
                            model_num)
    for titan_model_num in {'black', 'xp'}:
        nvidia['model_lines']['geforce gtx']['models'][
            'titan ' + titan_model_num] = nvidia['model_lines'][
                'titan']['models'].pop(titan_model_num)
    for titan_model_num in list(nvidia['model_lines'][
            'geforce gtx titan']['models'].keys()):
        nvidia['model_lines']['geforce gtx']['models'][
            'titan ' + titan_model_num] = nvidia['model_lines'][
                'geforce gtx titan']['models'].pop(titan_model_num)
    nvidia['model_lines']['geforce gtx']['models']['titan'] = nvidia[
        'model_lines']['geforce gtx']['models']['titan black']
    del nvidia['model_lines']['geforce gtx']['models']['titan ']
    del nvidia['model_lines']['geforce gtx titan']

    return nvidia


def main():
    """
    Download ffmpeg detection data.
    """
    data = dict(
        hwaccels=get_hwaccel_data(),
        nvidia=get_nvidia_data(),
    )
    json.dump(data, sys.stdout, indent=2)


if __name__ == '__main__':
    main()
