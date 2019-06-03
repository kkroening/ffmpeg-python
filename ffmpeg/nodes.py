from __future__ import unicode_literals

from past.builtins import basestring
from .dag import KwargReprNode
from ._utils import escape_chars, get_hash_int
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

    def __init__(
        self, upstream_node, upstream_label, node_types, upstream_selector=None
    ):
        if not _is_of_types(upstream_node, node_types):
            raise TypeError(
                'Expected upstream node to be of one of the following type(s): {}; got {}'.format(
                    _get_types_str(node_types), type(upstream_node)
                )
            )
        self.node = upstream_node
        self.label = upstream_label
        self.selector = upstream_selector

    def __hash__(self):
        return get_hash_int([hash(self.node), hash(self.label)])

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __repr__(self):
        node_repr = self.node.long_repr(include_hash=False)
        selector = ''
        if self.selector:
            selector = ':{}'.format(self.selector)
        out = '{}[{!r}{}] <{}>'.format(
            node_repr, self.label, selector, self.node.short_hash
        )
        return out

    def __getitem__(self, index):
        """
        Select a component (audio, video) of the stream.

        Example:
            Process the audio and video portions of a stream independently::

                input = ffmpeg.input('in.mp4')
                audio = input['a'].filter("aecho", 0.8, 0.9, 1000, 0.3)
                video = input['v'].hflip()
                out = ffmpeg.output(audio, video, 'out.mp4')
        """
        if self.selector is not None:
            raise ValueError('Stream already has a selector: {}'.format(self))
        elif not isinstance(index, basestring):
            raise TypeError("Expected string index (e.g. 'a'); got {!r}".format(index))
        return self.node.stream(label=self.label, selector=index)

    @property
    def audio(self):
        """Select the audio-portion of a stream.

        Some ffmpeg filters drop audio streams, and care must be taken
        to preserve the audio in the final output.  The ``.audio`` and
        ``.video`` operators can be used to reference the audio/video
        portions of a stream so that they can be processed separately
        and then re-combined later in the pipeline.  This dilemma is
        intrinsic to ffmpeg, and ffmpeg-python tries to stay out of the
        way while users may refer to the official ffmpeg documentation
        as to why certain filters drop audio.

        ``stream.audio`` is a shorthand for ``stream['a']``.

        Example:
            Process the audio and video portions of a stream independently::

                input = ffmpeg.input('in.mp4')
                audio = input.audio.filter("aecho", 0.8, 0.9, 1000, 0.3)
                video = input.video.hflip()
                out = ffmpeg.output(audio, video, 'out.mp4')
        """
        return self['a']

    @property
    def video(self):
        """Select the video-portion of a stream.

        Some ffmpeg filters drop audio streams, and care must be taken
        to preserve the audio in the final output.  The ``.audio`` and
        ``.video`` operators can be used to reference the audio/video
        portions of a stream so that they can be processed separately
        and then re-combined later in the pipeline.  This dilemma is
        intrinsic to ffmpeg, and ffmpeg-python tries to stay out of the
        way while users may refer to the official ffmpeg documentation
        as to why certain filters drop audio.

        ``stream.video`` is a shorthand for ``stream['v']``.

        Example:
            Process the audio and video portions of a stream independently::

                input = ffmpeg.input('in.mp4')
                audio = input.audio.filter("aecho", 0.8, 0.9, 1000, 0.3)
                video = input.video.hflip()
                out = ffmpeg.output(audio, video, 'out.mp4')
        """
        return self['v']


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
    for stream in list(stream_map.values()):
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
            raise ValueError(
                'Expected at least {} input stream(s); got {}'.format(
                    min_inputs, len(stream_map)
                )
            )
        elif max_inputs is not None and len(stream_map) > max_inputs:
            raise ValueError(
                'Expected at most {} input stream(s); got {}'.format(
                    max_inputs, len(stream_map)
                )
            )

    @classmethod
    def __check_input_types(cls, stream_map, incoming_stream_types):
        for stream in list(stream_map.values()):
            if not _is_of_types(stream, incoming_stream_types):
                raise TypeError(
                    'Expected incoming stream(s) to be of one of the following types: {}; got {}'.format(
                        _get_types_str(incoming_stream_types), type(stream)
                    )
                )

    @classmethod
    def __get_incoming_edge_map(cls, stream_map):
        incoming_edge_map = {}
        for downstream_label, upstream in list(stream_map.items()):
            incoming_edge_map[downstream_label] = (
                upstream.node,
                upstream.label,
                upstream.selector,
            )
        return incoming_edge_map

    def __init__(
        self,
        stream_spec,
        name,
        incoming_stream_types,
        outgoing_stream_type,
        min_inputs,
        max_inputs,
        args=[],
        kwargs={},
    ):
        stream_map = get_stream_map(stream_spec)
        self.__check_input_len(stream_map, min_inputs, max_inputs)
        self.__check_input_types(stream_map, incoming_stream_types)
        incoming_edge_map = self.__get_incoming_edge_map(stream_map)

        super(Node, self).__init__(incoming_edge_map, name, args, kwargs)
        self.__outgoing_stream_type = outgoing_stream_type
        self.__incoming_stream_types = incoming_stream_types

    def stream(self, label=None, selector=None):
        """Create an outgoing stream originating from this node.

        More nodes may be attached onto the outgoing stream.
        """
        return self.__outgoing_stream_type(self, label, upstream_selector=selector)

    def __getitem__(self, item):
        """Create an outgoing stream originating from this node; syntactic sugar for ``self.stream(label)``.
        It can also be used to apply a selector: e.g. ``node[0:'a']`` returns a stream with label 0 and
        selector ``'a'``, which is the same as ``node.stream(label=0, selector='a')``.

        Example:
            Process the audio and video portions of a stream independently::

                input = ffmpeg.input('in.mp4')
                audio = input[:'a'].filter("aecho", 0.8, 0.9, 1000, 0.3)
                video = input[:'v'].hflip()
                out = ffmpeg.output(audio, video, 'out.mp4')
        """
        if isinstance(item, slice):
            return self.stream(label=item.start, selector=item.stop)
        else:
            return self.stream(label=item)


class FilterableStream(Stream):
    def __init__(self, upstream_node, upstream_label, upstream_selector=None):
        super(FilterableStream, self).__init__(
            upstream_node, upstream_label, {InputNode, FilterNode}, upstream_selector
        )


# noinspection PyMethodOverriding
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
            kwargs=kwargs,
        )

    @property
    def short_repr(self):
        return os.path.basename(self.kwargs['filename'])


# noinspection PyMethodOverriding
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
            kwargs=kwargs,
        )

    """FilterNode"""

    def _get_filter(self, outgoing_edges):
        args = self.args
        kwargs = self.kwargs
        if self.name in ('split', 'asplit'):
            args = [len(outgoing_edges)]

        out_args = [escape_chars(x, '\\\'=:') for x in args]
        out_kwargs = {}
        for k, v in list(kwargs.items()):
            k = escape_chars(k, '\\\'=:')
            v = escape_chars(v, '\\\'=:')
            out_kwargs[k] = v

        arg_params = [escape_chars(v, '\\\'=:') for v in out_args]
        kwarg_params = ['{}={}'.format(k, out_kwargs[k]) for k in sorted(out_kwargs)]
        params = arg_params + kwarg_params

        params_text = escape_chars(self.name, '\\\'=:')

        if params:
            params_text += '={}'.format(':'.join(params))
        return escape_chars(params_text, '\\\'[],;')


# noinspection PyMethodOverriding
class OutputNode(Node):
    def __init__(self, stream, name, args=[], kwargs={}):
        super(OutputNode, self).__init__(
            stream_spec=stream,
            name=name,
            incoming_stream_types={FilterableStream},
            outgoing_stream_type=OutputStream,
            min_inputs=1,
            max_inputs=None,
            args=args,
            kwargs=kwargs,
        )

    @property
    def short_repr(self):
        return os.path.basename(self.kwargs['filename'])


class OutputStream(Stream):
    def __init__(self, upstream_node, upstream_label, upstream_selector=None):
        super(OutputStream, self).__init__(
            upstream_node,
            upstream_label,
            {OutputNode, GlobalNode, MergeOutputsNode},
            upstream_selector=upstream_selector,
        )


# noinspection PyMethodOverriding
class MergeOutputsNode(Node):
    def __init__(self, streams, name):
        super(MergeOutputsNode, self).__init__(
            stream_spec=streams,
            name=name,
            incoming_stream_types={OutputStream},
            outgoing_stream_type=OutputStream,
            min_inputs=1,
            max_inputs=None,
        )


# noinspection PyMethodOverriding
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
            kwargs=kwargs,
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


__all__ = ['Stream']
