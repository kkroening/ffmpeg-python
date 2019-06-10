from __future__ import unicode_literals

from builtins import str
from .dag import get_outgoing_edges
from ._run import topo_sort
import tempfile

from ffmpeg.nodes import (
    FilterNode,
    get_stream_spec_nodes,
    InputNode,
    OutputNode,
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
def view(stream_spec, detail=False, filename=None, pipe=False, **kwargs):
    try:
        import graphviz
    except ImportError:
        raise ImportError(
            'failed to import graphviz; please make sure graphviz is installed (e.g. `pip install '
            'graphviz`)'
        )

    show_labels = kwargs.pop('show_labels', True)
    if pipe and filename is not None:
        raise ValueError('Can\'t specify both `filename` and `pipe`')
    elif not pipe and filename is None:
        filename = tempfile.mktemp()

    nodes = get_stream_spec_nodes(stream_spec)

    sorted_nodes, outgoing_edge_maps = topo_sort(nodes)
    graph = graphviz.Digraph(format='png')
    graph.attr(rankdir='LR')
    if len(list(kwargs.keys())) != 0:
        raise ValueError(
            'Invalid kwargs key(s): {}'.format(', '.join(list(kwargs.keys())))
        )

    for node in sorted_nodes:
        color = _get_node_color(node)

        if detail:
            lines = [node.short_repr]
            lines += ['{!r}'.format(arg) for arg in node.args]
            lines += [
                '{}={!r}'.format(key, node.kwargs[key]) for key in sorted(node.kwargs)
            ]
            node_text = '\n'.join(lines)
        else:
            node_text = node.short_repr
        graph.node(
            str(hash(node)), node_text, shape='box', style='filled', fillcolor=color
        )
        outgoing_edge_map = outgoing_edge_maps.get(node, {})

        for edge in get_outgoing_edges(node, outgoing_edge_map):
            kwargs = {}
            up_label = edge.upstream_label
            down_label = edge.downstream_label
            up_selector = edge.upstream_selector

            if show_labels and (
                up_label is not None
                or down_label is not None
                or up_selector is not None
            ):
                if up_label is None:
                    up_label = ''
                if up_selector is not None:
                    up_label += ":" + up_selector
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

    if pipe:
        return graph.pipe()
    else:
        graph.view(filename, cleanup=True)
        return stream_spec


__all__ = ['view']
