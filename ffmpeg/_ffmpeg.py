from __future__ import unicode_literals

from past.builtins import basestring
from ._utils import basestring

from .nodes import (
    filter_operator,
    GlobalNode,
    InputNode,
    MergeOutputsNode,
    OutputNode,
    output_operator,
)


def input(filename, **kwargs):
    """Input file URL (ffmpeg ``-i`` option)

    Any supplied kwargs are passed to ffmpeg verbatim (e.g. ``t=20``,
    ``f='mp4'``, ``acodec='pcm'``, etc.).

    To tell ffmpeg to read from stdin, use ``pipe:`` as the filename.

    Official documentation: `Main options <https://ffmpeg.org/ffmpeg.html#Main-options>`__
    """
    kwargs['filename'] = filename
    fmt = kwargs.pop('f', None)
    if fmt:
        if 'format' in kwargs:
            raise ValueError("Can't specify both `format` and `f` kwargs")
        kwargs['format'] = fmt
    return InputNode(input.__name__, kwargs=kwargs).stream()


@output_operator()
def global_args(stream, *args):
    """Add extra global command-line argument(s), e.g. ``-progress``.
    """
    return GlobalNode(stream, global_args.__name__, args).stream()


@output_operator()
def overwrite_output(stream):
    """Overwrite output files without asking (ffmpeg ``-y`` option)

    Official documentation: `Main options <https://ffmpeg.org/ffmpeg.html#Main-options>`__
    """
    return GlobalNode(stream, overwrite_output.__name__, ['-y']).stream()


@output_operator()
def merge_outputs(*streams):
    """Include all given outputs in one ffmpeg command line
    """
    return MergeOutputsNode(streams, merge_outputs.__name__).stream()


@filter_operator()
def output(*streams_and_filename, **kwargs):
    """Output file URL

    Syntax:
        `ffmpeg.output(stream1[, stream2, stream3...], filename, **ffmpeg_args)`

    Any supplied keyword arguments are passed to ffmpeg verbatim (e.g.
    ``t=20``, ``f='mp4'``, ``acodec='pcm'``, ``vcodec='rawvideo'``,
    etc.).  Some keyword-arguments are handled specially, as shown below.

    Args:
        video_bitrate: parameter for ``-b:v``, e.g. ``video_bitrate=1000``.
        audio_bitrate: parameter for ``-b:a``, e.g. ``audio_bitrate=200``.
        format: alias for ``-f`` parameter, e.g. ``format='mp4'``
            (equivalent to ``f='mp4'``).

    If multiple streams are provided, they are mapped to the same
    output.

    To tell ffmpeg to write to stdout, use ``pipe:`` as the filename.

    Official documentation: `Synopsis <https://ffmpeg.org/ffmpeg.html#Synopsis>`__
    """
    streams_and_filename = list(streams_and_filename)
    if 'filename' not in kwargs:
        if not isinstance(streams_and_filename[-1], basestring):
            raise ValueError('A filename must be provided')
        kwargs['filename'] = streams_and_filename.pop(-1)
    streams = streams_and_filename

    fmt = kwargs.pop('f', None)
    if fmt:
        if 'format' in kwargs:
            raise ValueError("Can't specify both `format` and `f` kwargs")
        kwargs['format'] = fmt
    return OutputNode(streams, output.__name__, kwargs=kwargs).stream()


__all__ = ['input', 'merge_outputs', 'output', 'overwrite_output']
