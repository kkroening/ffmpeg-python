from __future__ import unicode_literals
from .nodes import (
    FilterNode,
    GlobalNode,
    InputNode,
    operator,
    OutputNode,
)


def input(filename, **kwargs):
    """Input file URL (ffmpeg ``-i`` option)

    Official documentation: `Main options <https://ffmpeg.org/ffmpeg.html#Main-options>`__
    """
    kwargs['filename'] = filename
    fmt = kwargs.pop('f', None)
    if fmt:
        assert 'format' not in kwargs, "Can't specify both `format` and `f` kwargs"
        kwargs['format'] = fmt
    return InputNode(input.__name__, **kwargs)


@operator(node_classes={OutputNode, GlobalNode})
def overwrite_output(parent_node):
    """Overwrite output files without asking (ffmpeg ``-y`` option)

    Official documentation: `Main options <https://ffmpeg.org/ffmpeg.html#Main-options>`__
    """
    return GlobalNode(parent_node, overwrite_output.__name__)


@operator(node_classes={OutputNode})
def merge_outputs(*parent_nodes):
    return OutputNode(parent_nodes, merge_outputs.__name__)


@operator(node_classes={InputNode, FilterNode})
def output(parent_node, filename, **kwargs):
    """Output file URL

    Official documentation: `Synopsis <https://ffmpeg.org/ffmpeg.html#Synopsis>`__
    """
    kwargs['filename'] = filename
    fmt = kwargs.pop('f', None)
    if fmt:
        assert 'format' not in kwargs, "Can't specify both `format` and `f` kwargs"
        kwargs['format'] = fmt
    return OutputNode([parent_node], output.__name__, **kwargs)



__all__ = [
    'input',
    'merge_outputs',
    'output',
    'overwrite_output',
]
