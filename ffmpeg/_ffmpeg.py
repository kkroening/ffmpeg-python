from .nodes import (
    FilterNode,
    GlobalNode,
    InputNode,
    operator,
    OutputNode,
)


def file_input(filename):
    return InputNode(file_input.__name__, filename=filename)


@operator(node_classes={OutputNode, GlobalNode})
def overwrite_output(parent):
    return GlobalNode(parent, overwrite_output.__name__)


@operator(node_classes={OutputNode})
def merge_outputs(*parents):
    return OutputNode(parents, merge_outputs.__name__)


@operator(node_classes={InputNode, FilterNode})
def file_output(parent, filename):
    return OutputNode([parent], file_output.__name__, filename=filename)


__all__ = [
    'file_input',
    'file_output',
    'merge_outputs',
    'overwrite_output',
]
