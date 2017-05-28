from distutils.core import setup
from ffmpeg._filters import __all__ as filter_names
from textwrap import dedent
import subprocess


def get_current_commit_hash():
    p = subprocess.Popen(['git', 'rev-parse', 'HEAD'], stdout=subprocess.PIPE)
    commit_hash = p.communicate()[0].strip()
    assert p.returncode == 0, '`git rev-parse HEAD` failed'
    return commit_hash


long_description = dedent("""
    ffmpeg-python: Python bindings for FFmpeg
    =========================================

    :Github: https://github.com/kkroening/ffmpeg-python
    :API Reference: https://kkroening.github.io/ffmpeg-python/
""")



commit_hash = get_current_commit_hash()
download_url = 'https://github.com/kkroening/ffmpeg-python/archive/{}.zip'.format(commit_hash)

file_formats = [
    'aac',
    'ac3',
    'avi',
    'bmp'
    'flac',
    'gif',
    'mov',
    'mp3',
    'mp4',
    'png',
    'raw',
    'rawvideo',
    'wav',
]
file_formats += ['.{}'.format(x) for x in file_formats]

misc_keywords = [
    '-vf',
    'a/v',
    'audio',
    'dsp',
    'FFmpeg',
    'ffmpeg',
    'ffprobe',
    'filtering',
    'filter_complex',
    'movie',
    'render',
    'signals',
    'sound',
    'streaming',
    'streams',
    'vf',
    'video',
    'wrapper',
]

keywords = misc_keywords + file_formats + filter_names

setup(
    name = 'ffmpeg-python',
    packages = ['ffmpeg'],
    version = '0.1.2',
    description = 'Python bindings for FFmpeg - with support for complex filtering',
    author = 'Karl Kroening',
    author_email = 'karlk@kralnet.us',
    url = 'https://github.com/kkroening/ffmpeg-python',
    download_url = download_url,
    classifiers = [],
    keywords = keywords,
    long_description = long_description,
)
