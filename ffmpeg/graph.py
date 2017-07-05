from __future__ import unicode_literals

from .dag import get_outgoing_edges
from ._run import topo_sort
import graphviz
import os

from ffmpeg.nodes import (
    InputNode,
    OutputNode,
    FilterNode,
    operator,
)


@operator()
def view(*downstream_nodes, **kwargs):
    sorted_nodes, outgoing_edge_maps = topo_sort(downstream_nodes)
    graph = graphviz.Digraph()
    graph.attr(rankdir='LR')
    show_labels = kwargs.pop('show_labels', False)
    if len(kwargs.keys()) != 0:
        raise ValueError('Invalid kwargs key(s): {}'.format(', '.join(kwargs.keys())))

    for node in sorted_nodes:
        name = node.name
        if '_kwargs' in dir(node) and 'filename' in node._kwargs:
            name = os.path.basename(node._kwargs['filename'])
        if isinstance(node, InputNode):
            color = '#99cc00'
        elif isinstance(node, OutputNode):
            color = '#99ccff'
        elif isinstance(node, FilterNode):
            color = '#ffcc00'
        else:
            color = None
        graph.node(str(hash(node)), name, shape='box', style='filled', fillcolor=color)
        outgoing_edge_map = outgoing_edge_maps.get(node, {})
        for edge in get_outgoing_edges(node, outgoing_edge_map):
            kwargs = {}
            if show_labels:
                kwargs['label'] = '{} -> {}'.format(edge.upstream_label, edge.downstream_label)
            upstream_node_id = str(hash(edge.upstream_node))
            downstream_node_id = str(hash(edge.downstream_node))
            graph.edge(upstream_node_id, downstream_node_id, **kwargs)

    graph.view('graph.png')
