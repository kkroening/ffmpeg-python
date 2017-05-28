from .nodes import (
    FilterNode,
    GlobalNode,
    InputNode,
    operator,
    OutputNode,
)


def file_input(filename):
    """Input file URL (ffmpeg ``-i`` option)

    Official documentation: `Main options <https://ffmpeg.org/ffmpeg.html#Main-options>`__
    """
    return InputNode(file_input.__name__, filename=filename)


def input(filename):
    """Shorthand for ``file_input``"""
    return file_input(filename)


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
def file_output(parent_node, filename):
    """Output file URL

    Official documentation: `Synopsis <https://ffmpeg.org/ffmpeg.html#Synopsis>`__
    """
    return OutputNode([parent_node], file_output.__name__, filename=filename)


@operator(node_classes={InputNode, FilterNode})
def output(parent_node, filename):
    """Shorthand for ``file_output``"""
    return file_output(parent_node, filename)



__all__ = [
    'file_input',
    'file_output',
    'input',
    'merge_outputs',
    'output',
    'overwrite_output',
]
