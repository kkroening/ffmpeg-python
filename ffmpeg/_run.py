from __future__ import unicode_literals

from functools import reduce
from past.builtins import basestring
import copy
import operator as _operator
import subprocess as _subprocess

from ._ffmpeg import (
    input,
    merge_outputs,
    output,
    overwrite_output,
)
from .nodes import (
    GlobalNode,
    InputNode,   
    operator,
    OutputNode,
)

def _get_stream_name(name):
    return '[{}]'.format(name)


def _convert_kwargs_to_cmd_line_args(kwargs):
    args = []
    for k in sorted(kwargs.keys()):
        v = kwargs[k]
        args.append('-{}'.format(k))
        if v:
            args.append('{}'.format(v))
    return args


def _get_input_args(input_node):
    if input_node._name == input.__name__:
        kwargs = copy.copy(input_node._kwargs)
        filename = kwargs.pop('filename')
        fmt = kwargs.pop('format', None)
        video_size = kwargs.pop('video_size', None)
        args = []
        if fmt:
            args += ['-f', fmt]
        if video_size:
            args += ['-video_size', '{}x{}'.format(video_size[0], video_size[1])]
        args += _convert_kwargs_to_cmd_line_args(kwargs)
        args += ['-i', filename]
    else:
        assert False, 'Unsupported input node: {}'.format(input_node)
    return args


def _topo_sort(start_node):
    marked_nodes = []
    sorted_nodes = []
    child_map = {}
    def visit(node, child):
        assert node not in marked_nodes, 'Graph is not a DAG'
        if child is not None:
            if node not in child_map:
                child_map[node] = []
            child_map[node].append(child)
        if node not in sorted_nodes:
            marked_nodes.append(node)
            [visit(parent, node) for parent in node._parents]
            marked_nodes.remove(node)
            sorted_nodes.append(node)
    unmarked_nodes = [start_node]
    while unmarked_nodes:
        visit(unmarked_nodes.pop(), None)
    return sorted_nodes, child_map


def _get_filter_spec(i, node, stream_name_map):
    stream_name = _get_stream_name('v{}'.format(i))
    stream_name_map[node] = stream_name
    inputs = [stream_name_map[parent] for parent in node._parents]
    filter_spec = '{}{}{}'.format(''.join(inputs), node._get_filter(), stream_name)
    return filter_spec


def _get_filter_arg(filter_nodes, stream_name_map):
    filter_specs = [_get_filter_spec(i, node, stream_name_map) for i, node in enumerate(filter_nodes)]
    return ';'.join(filter_specs)


def _get_global_args(node):
    if node._name == overwrite_output.__name__:
        return ['-y']
    else:
        assert False, 'Unsupported global node: {}'.format(node)


def _get_output_args(node, stream_name_map):
    args = []
    if node._name != merge_outputs.__name__:
        stream_name = stream_name_map[node._parents[0]]
        if stream_name != '[0]':
            args += ['-map', stream_name]
        if node._name == output.__name__:
            kwargs = copy.copy(node._kwargs)
            filename = kwargs.pop('filename')
            fmt = kwargs.pop('format', None)
            if fmt:
                args += ['-f', fmt]
            args += _convert_kwargs_to_cmd_line_args(kwargs)
            args += [filename]
        else:
            assert False, 'Unsupported output node: {}'.format(node)
    return args


@operator(node_classes={OutputNode, GlobalNode})
def get_args(node):
    """Get command-line arguments for ffmpeg."""
    args = []
    # TODO: group nodes together, e.g. `-i somefile -r somerate`.
    sorted_nodes, child_map = _topo_sort(node)
    del(node)
    input_nodes = [node for node in sorted_nodes if isinstance(node, InputNode)]
    output_nodes = [node for node in sorted_nodes if isinstance(node, OutputNode) and not
        isinstance(node, GlobalNode)]
    global_nodes = [node for node in sorted_nodes if isinstance(node, GlobalNode)]
    filter_nodes = [node for node in sorted_nodes if node not in (input_nodes + output_nodes + global_nodes)]
    stream_name_map = {node: _get_stream_name(i) for i, node in enumerate(input_nodes)}
    filter_arg = _get_filter_arg(filter_nodes, stream_name_map)
    args += reduce(_operator.add, [_get_input_args(node) for node in input_nodes])
    if filter_arg:
        args += ['-filter_complex', filter_arg]
    args += reduce(_operator.add, [_get_output_args(node, stream_name_map) for node in output_nodes])
    args += reduce(_operator.add, [_get_global_args(node) for node in global_nodes], [])
    return args


@operator(node_classes={OutputNode, GlobalNode})
def run(node, cmd='ffmpeg'):
    """Run ffmpeg on node graph."""
    if isinstance(cmd, basestring):
        cmd = [cmd]
    elif type(cmd) != list:
        cmd = list(cmd)
    args = cmd + node.get_args()
    _subprocess.check_call(args)


__all__ = [
    'get_args',
    'run',
]
