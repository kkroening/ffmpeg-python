from __future__ import unicode_literals

from .nodes import (
    filter_operator,
    GlobalNode,
    InputNode,
    MergeOutputsNode,
    OutputNode,
    output_operator,
    SourceNode)


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



def source_multi_output(filter_name, *args, **kwargs):
    """Apply custom filter with one or more outputs.

    This is the same as ``filter_`` except that the filter can produce more than one output.

    To reference an output stream, use either the ``.stream`` operator or bracket shorthand:

    Example:

        ```
        split = ffmpeg.input('in.mp4').filter_multi_output('split')
        split0 = split.stream(0)
        split1 = split[1]
        ffmpeg.concat(split0, split1).output('out.mp4').run()
        ```
    """
    return SourceNode(filter_name, args=args, kwargs=kwargs)


def source(filter_name, *args, **kwargs):
    return source_multi_output(filter_name, *args, **kwargs).stream()


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
def output(stream, filename, **kwargs):
    """Output file URL

    Official documentation: `Synopsis <https://ffmpeg.org/ffmpeg.html#Synopsis>`__
    """
    kwargs['filename'] = filename
    fmt = kwargs.pop('f', None)
    if fmt:
        if 'format' in kwargs:
            raise ValueError("Can't specify both `format` and `f` kwargs")
        kwargs['format'] = fmt
    return OutputNode(stream, output.__name__, kwargs=kwargs).stream()



__all__ = [
    'input',
    'source_multi_output',
    'source',
    'merge_outputs',
    'output',
    'overwrite_output',
]
