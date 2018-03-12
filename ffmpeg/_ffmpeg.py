from __future__ import unicode_literals

from ._utils import basestring

from .nodes import (
    filter_operator,
    GlobalNode,
    InputNode,
    MergeOutputsNode,
    OutputNode,
    output_operator,
    OutputStream)


def input(filename, **kwargs):
    """Input file URL (ffmpeg ``-i`` option)

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
def overwrite_output(stream):
    """Overwrite output files without asking (ffmpeg ``-y`` option)

    Official documentation: `Main options <https://ffmpeg.org/ffmpeg.html#Main-options>`__
    """
    return GlobalNode(stream, overwrite_output.__name__).stream()


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

        If multiple streams are provided, they are mapped to the same output.

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


@output_operator()
def map(*streams):
    """Map multiple streams to the same output
    """
    head = streams[0]
    tail = streams[1:]

    if not isinstance(head, OutputStream):
        raise ValueError('First argument must be an output stream')

    if not tail:
        return head

    return OutputNode(head.node, tail).stream()


__all__ = [
    'input',
    'merge_outputs',
    'output',
    'map',
    'overwrite_output',
]
