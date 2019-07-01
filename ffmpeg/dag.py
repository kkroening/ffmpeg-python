from __future__ import unicode_literals

from ._utils import get_hash, get_hash_int
from builtins import object
from collections import namedtuple


class DagNode(object):
    """Node in a directed-acyclic graph (DAG).

    Edges:
        DagNodes are connected by edges.  An edge connects two nodes with a label for each side:
         - ``upstream_node``: upstream/parent node
         - ``upstream_label``: label on the outgoing side of the upstream node
         - ``downstream_node``: downstream/child node
         - ``downstream_label``: label on the incoming side of the downstream node

        For example, DagNode A may be connected to DagNode B with an edge labelled "foo" on A's side, and "bar" on B's
        side:

           _____               _____
          |     |             |     |
          |  A  >[foo]---[bar]>  B  |
          |_____|             |_____|

        Edge labels may be integers or strings, and nodes cannot have more than one incoming edge with the same label.

        DagNodes may have any number of incoming edges and any number of outgoing edges.  DagNodes keep track only of
        their incoming edges, but the entire graph structure can be inferred by looking at the furthest downstream
        nodes and working backwards.

    Hashing:
        DagNodes must be hashable, and two nodes are considered to be equivalent if they have the same hash value.

        Nodes are immutable, and the hash should remain constant as a result.  If a node with new contents is required,
        create a new node and throw the old one away.

    String representation:
        In order for graph visualization tools to show useful information, nodes must be representable as strings.  The
        ``repr`` operator should provide a more or less "full" representation of the node, and the ``short_repr``
        property should be a shortened, concise representation.

        Again, because nodes are immutable, the string representations should remain constant.
    """

    def __hash__(self):
        """Return an integer hash of the node."""
        raise NotImplementedError()

    def __eq__(self, other):
        """Compare two nodes; implementations should return True if (and only if) hashes match."""
        raise NotImplementedError()

    def __repr__(self, other):
        """Return a full string representation of the node."""
        raise NotImplementedError()

    @property
    def short_repr(self):
        """Return a partial/concise representation of the node."""
        raise NotImplementedError()

    @property
    def incoming_edge_map(self):
        """Provides information about all incoming edges that connect to this node.

        The edge map is a dictionary that maps an ``incoming_label`` to ``(outgoing_node, outgoing_label)``.  Note that
        implicity, ``incoming_node`` is ``self``.  See "Edges" section above.
        """
        raise NotImplementedError()


DagEdge = namedtuple(
    'DagEdge',
    [
        'downstream_node',
        'downstream_label',
        'upstream_node',
        'upstream_label',
        'upstream_selector',
    ],
)


def get_incoming_edges(downstream_node, incoming_edge_map):
    edges = []
    for downstream_label, upstream_info in list(incoming_edge_map.items()):
        upstream_node, upstream_label, upstream_selector = upstream_info
        edges += [
            DagEdge(
                downstream_node,
                downstream_label,
                upstream_node,
                upstream_label,
                upstream_selector,
            )
        ]
    return edges


def get_outgoing_edges(upstream_node, outgoing_edge_map):
    edges = []
    for upstream_label, downstream_infos in sorted(outgoing_edge_map.items()):
        for downstream_info in downstream_infos:
            downstream_node, downstream_label, downstream_selector = downstream_info
            edges += [
                DagEdge(
                    downstream_node,
                    downstream_label,
                    upstream_node,
                    upstream_label,
                    downstream_selector,
                )
            ]
    return edges


class KwargReprNode(DagNode):
    """A DagNode that can be represented as a set of args+kwargs.
    """

    @property
    def __upstream_hashes(self):
        hashes = []
        for downstream_label, upstream_info in list(self.incoming_edge_map.items()):
            upstream_node, upstream_label, upstream_selector = upstream_info
            hashes += [
                hash(x)
                for x in [
                    downstream_label,
                    upstream_node,
                    upstream_label,
                    upstream_selector,
                ]
            ]
        return hashes

    @property
    def __inner_hash(self):
        props = {'args': self.args, 'kwargs': self.kwargs}
        return get_hash(props)

    def __get_hash(self):
        hashes = self.__upstream_hashes + [self.__inner_hash]
        return get_hash_int(hashes)

    def __init__(self, incoming_edge_map, name, args, kwargs):
        self.__incoming_edge_map = incoming_edge_map
        self.name = name
        self.args = args
        self.kwargs = kwargs
        self.__hash = self.__get_hash()

    def __hash__(self):
        return self.__hash

    def __eq__(self, other):
        return hash(self) == hash(other)

    @property
    def short_hash(self):
        return '{:x}'.format(abs(hash(self)))[:12]

    def long_repr(self, include_hash=True):
        formatted_props = ['{!r}'.format(arg) for arg in self.args]
        formatted_props += [
            '{}={!r}'.format(key, self.kwargs[key]) for key in sorted(self.kwargs)
        ]
        out = '{}({})'.format(self.name, ', '.join(formatted_props))
        if include_hash:
            out += ' <{}>'.format(self.short_hash)
        return out

    def __repr__(self):
        return self.long_repr()

    @property
    def incoming_edges(self):
        return get_incoming_edges(self, self.incoming_edge_map)

    @property
    def incoming_edge_map(self):
        return self.__incoming_edge_map

    @property
    def short_repr(self):
        return self.name


def topo_sort(downstream_nodes):
    marked_nodes = []
    sorted_nodes = []
    outgoing_edge_maps = {}

    def visit(
        upstream_node,
        upstream_label,
        downstream_node,
        downstream_label,
        downstream_selector=None,
    ):
        if upstream_node in marked_nodes:
            raise RuntimeError('Graph is not a DAG')

        if downstream_node is not None:
            outgoing_edge_map = outgoing_edge_maps.get(upstream_node, {})
            outgoing_edge_infos = outgoing_edge_map.get(upstream_label, [])
            outgoing_edge_infos += [
                (downstream_node, downstream_label, downstream_selector)
            ]
            outgoing_edge_map[upstream_label] = outgoing_edge_infos
            outgoing_edge_maps[upstream_node] = outgoing_edge_map

        if upstream_node not in sorted_nodes:
            marked_nodes.append(upstream_node)
            for edge in upstream_node.incoming_edges:
                visit(
                    edge.upstream_node,
                    edge.upstream_label,
                    edge.downstream_node,
                    edge.downstream_label,
                    edge.upstream_selector,
                )
            marked_nodes.remove(upstream_node)
            sorted_nodes.append(upstream_node)

    unmarked_nodes = [(node, None) for node in downstream_nodes]
    while unmarked_nodes:
        upstream_node, upstream_label = unmarked_nodes.pop()
        visit(upstream_node, upstream_label, None, None)
    return sorted_nodes, outgoing_edge_maps
