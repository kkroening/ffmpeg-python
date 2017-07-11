from __future__ import unicode_literals

from .dag import KwargReprNode
from ._utils import get_hash_int
from builtins import object
import os


def _is_of_types(obj, types):
    valid = False
    for stream_type in types:
        if isinstance(obj, stream_type):
            valid = True
            break
    return valid


def _get_types_str(types):
    return ', '.join(['{}.{}'.format(x.__module__, x.__name__) for x in types])


class Stream(object):
    """Represents the outgoing edge of an upstream node; may be used to create more downstream nodes."""
    def __init__(self, upstream_node, upstream_label, node_types):
        if not _is_of_types(upstream_node, node_types):
            raise TypeError('Expected upstream node to be of one of the following type(s): {}; got {}'.format(
                _get_types_str(node_types), type(upstream_node)))
        self.node = upstream_node
        self.label = upstream_label

    def __hash__(self):
        return get_hash_int([hash(self.node), hash(self.label)])

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __repr__(self):
        node_repr = self.node.long_repr(include_hash=False)
        out = '{}[{!r}] <{}>'.format(node_repr, self.label, self.node.short_hash)
        return out


def get_stream_map(stream_spec):
    if stream_spec is None:
        stream_map = {}
    elif isinstance(stream_spec, Stream):
        stream_map = {None: stream_spec}
    elif isinstance(stream_spec, (list, tuple)):
        stream_map = dict(enumerate(stream_spec))
    elif isinstance(stream_spec, dict):
        stream_map = stream_spec
    return stream_map


def get_stream_map_nodes(stream_map):
    nodes = []
    for stream in stream_map.values():
        if not isinstance(stream, Stream):
            raise TypeError('Expected Stream; got {}'.format(type(stream)))
        nodes.append(stream.node)
    return nodes


def get_stream_spec_nodes(stream_spec):
    stream_map = get_stream_map(stream_spec)
    return get_stream_map_nodes(stream_map)


class Node(KwargReprNode):
    """Node base"""
    @classmethod
    def __check_input_len(cls, stream_map, min_inputs, max_inputs):
        if min_inputs is not None and len(stream_map) < min_inputs:
            raise ValueError('Expected at least {} input stream(s); got {}'.format(min_inputs, len(stream_map)))
        elif max_inputs is not None and len(stream_map) > max_inputs:
            raise ValueError('Expected at most {} input stream(s); got {}'.format(max_inputs, len(stream_map)))

    @classmethod
    def __check_input_types(cls, stream_map, incoming_stream_types):
        for stream in list(stream_map.values()):
            if not _is_of_types(stream, incoming_stream_types):
                raise TypeError('Expected incoming stream(s) to be of one of the following types: {}; got {}'
                    .format(_get_types_str(incoming_stream_types), type(stream)))

    @classmethod
    def __get_incoming_edge_map(cls, stream_map):
        incoming_edge_map = {}
        for downstream_label, upstream in list(stream_map.items()):
            incoming_edge_map[downstream_label] = (upstream.node, upstream.label)
        return incoming_edge_map

    def __init__(self, stream_spec, name, incoming_stream_types, outgoing_stream_type, min_inputs, max_inputs, args=[],
            kwargs={}):
        stream_map = get_stream_map(stream_spec)
        self.__check_input_len(stream_map, min_inputs, max_inputs)
        self.__check_input_types(stream_map, incoming_stream_types)
        incoming_edge_map = self.__get_incoming_edge_map(stream_map)
        super(Node, self).__init__(incoming_edge_map, name, args, kwargs)
        self.__outgoing_stream_type = outgoing_stream_type

    def stream(self, label=None):
        """Create an outgoing stream originating from this node.

        More nodes may be attached onto the outgoing stream.
        """
        return self.__outgoing_stream_type(self, label)

    def __getitem__(self, label):
        """Create an outgoing stream originating from this node; syntactic sugar for ``self.stream(label)``.
        """
        return self.stream(label)


class FilterableStream(Stream):
    def __init__(self, upstream_node, upstream_label):
        super(FilterableStream, self).__init__(upstream_node, upstream_label, {InputNode, FilterNode})


class InputNode(Node):
    """InputNode type"""
    def __init__(self, name, args=[], kwargs={}):
        super(InputNode, self).__init__(
            stream_spec=None,
            name=name,
            incoming_stream_types={},
            outgoing_stream_type=FilterableStream,
            min_inputs=0,
            max_inputs=0,
            args=args,
            kwargs=kwargs
        )

    @property
    def short_repr(self):
        return os.path.basename(self.kwargs['filename'])


class FilterNode(Node):
    def __init__(self, stream_spec, name, max_inputs=1, args=[], kwargs={}):
        super(FilterNode, self).__init__(
            stream_spec=stream_spec,
            name=name,
            incoming_stream_types={FilterableStream},
            outgoing_stream_type=FilterableStream,
            min_inputs=1,
            max_inputs=max_inputs,
            args=args,
            kwargs=kwargs
        )

    def _get_filter(self, outgoing_edges):
        args = self.args
        kwargs = self.kwargs
        if self.name == 'split':
            args = [len(outgoing_edges)]

        arg_params = ['{}'.format(arg) for arg in args]
        kwarg_params = ['{}={}'.format(k, kwargs[k]) for k in sorted(kwargs)]
        params = arg_params + kwarg_params

        params_text = self.name
        if params:
            params_text += '={}'.format(':'.join(params))
        return params_text


class OutputNode(Node):
    def __init__(self, stream, name, args=[], kwargs={}):
        super(OutputNode, self).__init__(
            stream_spec=stream,
            name=name,
            incoming_stream_types={FilterableStream},
            outgoing_stream_type=OutputStream,
            min_inputs=1,
            max_inputs=1,
            args=args,
            kwargs=kwargs
        )

    @property
    def short_repr(self):
        return os.path.basename(self.kwargs['filename'])


class OutputStream(Stream):
    def __init__(self, upstream_node, upstream_label):
        super(OutputStream, self).__init__(upstream_node, upstream_label, {OutputNode, GlobalNode, MergeOutputsNode})


class MergeOutputsNode(Node):
    def __init__(self, streams, name):
        super(MergeOutputsNode, self).__init__(
            stream_spec=streams,
            name=name,
            incoming_stream_types={OutputStream},
            outgoing_stream_type=OutputStream,
            min_inputs=1,
            max_inputs=None
        )


class GlobalNode(Node):
    def __init__(self, stream, name, args=[], kwargs={}):
        super(GlobalNode, self).__init__(
            stream_spec=stream,
            name=name,
            incoming_stream_types={OutputStream},
            outgoing_stream_type=OutputStream,
            min_inputs=1,
            max_inputs=1,
            args=args,
            kwargs=kwargs
        )


def stream_operator(stream_classes={Stream}, name=None):
    def decorator(func):
        func_name = name or func.__name__
        [setattr(stream_class, func_name, func) for stream_class in stream_classes]
        return func
    return decorator


def filter_operator(name=None):
    return stream_operator(stream_classes={FilterableStream}, name=name)


def output_operator(name=None):
    return stream_operator(stream_classes={OutputStream}, name=name)
