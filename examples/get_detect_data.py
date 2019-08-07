#!/usr/bin/env python
"""
Retrieve and process all the external data for hardware detection.
"""

import sys
import json

import requests
import pandas

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
PLATFORM_TO_PY = {
    'Apple': 'Darwin',
}


def main():
    data = {}

    data['hwaccels'] = hwaccels = {}
    response = requests.get(HWACCELINTRO_URL)
    api_avail_table, impl_table = pandas.read_html(response.content)

    gpu_vendor_cols = api_avail_table.loc[1][1:]
    platform_cols = api_avail_table.loc[0][1:]
    api_rows = api_avail_table[0][2:]

    hwaccels['api_avail'] = platforms = {}
    for gpu_vendor_idx, gpu_vendor in enumerate(gpu_vendor_cols):
        platform = platform_cols[gpu_vendor_idx + 1]
        platform = PLATFORM_TO_PY.get(platform, platform)
        gpu_vendors = platforms.setdefault(platform, {})
        avail_hwaccels = gpu_vendors.setdefault(gpu_vendor, [])
        for api_idx, api in enumerate(api_rows):
            if api_avail_table[gpu_vendor_idx + 1][api_idx + 2] != 'N':
                avail_hwaccels.append(API_TO_HWACCEL[api])

    json.dump(data, sys.stdout, indent=2)


if __name__ == '__main__':
    main()
