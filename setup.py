from ffmpeg._filters import __all__ as filter_names
from distutils.core import setup


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
    version = '0.1.1',
    description = 'Python bindings for FFmpeg - with support for complex filtering',
    author = 'Karl Kroening',
    author_email = 'karlk@kralnet.us',
    url = 'https://github.com/kkroening/ffmpeg-python',
    download_url = 'https://github.com/kkroening/ffmpeg-python/archive/0.1.1.tar.gz',
    classifiers = [],
    keywords = keywords,
)
