from __future__ import unicode_literals

from .dag import get_outgoing_edges
from ._run import topo_sort
import os
import tempfile

from ffmpeg.nodes import (
    FilterNode,
    InputNode,
    OutputNode,
    Stream,
    stream_operator,
)


_RIGHT_ARROW = '\u2192'


def _get_node_color(node):
    if isinstance(node, InputNode):
        color = '#99cc00'
    elif isinstance(node, OutputNode):
        color = '#99ccff'
    elif isinstance(node, FilterNode):
        color = '#ffcc00'
    else:
        color = None
    return color


@stream_operator()
def view(*streams, **kwargs):
    try:
        import graphviz
    except ImportError:
        raise ImportError('failed to import graphviz; please make sure graphviz is installed (e.g. `pip install '
            'graphviz`)')

    filename = kwargs.pop('filename', None)
    show_labels = kwargs.pop('show_labels', True)
    if filename is None:
        filename = tempfile.mktemp()

    nodes = []
    for stream in streams:
        if not isinstance(stream, Stream):
            raise TypeError('Expected Stream; got {}'.format(type(stream)))
        nodes.append(stream.node)

    sorted_nodes, outgoing_edge_maps = topo_sort(nodes)
    graph = graphviz.Digraph()
    graph.attr(rankdir='LR')
    if len(kwargs.keys()) != 0:
        raise ValueError('Invalid kwargs key(s): {}'.format(', '.join(kwargs.keys())))

    for node in sorted_nodes:
        name = node.name
        if '_kwargs' in dir(node) and 'filename' in node._kwargs:
            name = os.path.basename(node._kwargs['filename'])
        color = _get_node_color(node)

        graph.node(str(hash(node)), name, shape='box', style='filled', fillcolor=color)
        outgoing_edge_map = outgoing_edge_maps.get(node, {})

        for edge in get_outgoing_edges(node, outgoing_edge_map):
            kwargs = {}
            up_label = edge.upstream_label
            down_label = edge.downstream_label
            if show_labels and (up_label is not None or down_label is not None):
                if up_label is None:
                    up_label = ''
                if down_label is None:
                    down_label = ''
                if up_label != '' and down_label != '':
                    middle = ' {} '.format(_RIGHT_ARROW)
                else:
                    middle = ''
                kwargs['label'] = '{}  {}  {}'.format(up_label, middle, down_label)
            upstream_node_id = str(hash(edge.upstream_node))
            downstream_node_id = str(hash(edge.downstream_node))
            graph.edge(upstream_node_id, downstream_node_id, **kwargs)

    graph.view(filename)



__all__ = [
    'view',
]
