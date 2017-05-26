#!./venv/bin/python

from functools import partial
import hashlib
import json
import operator
import subprocess
import sys


def _create_root_node(node_class, *args, **kwargs):
    root = node_class(*args, **kwargs)
    root._update_hash()
    return root


def _create_child_node(node_class, parent, *args, **kwargs):
    child = node_class(parent, *args, **kwargs)
    child._update_hash()
    return child


class _Node(object):
    def __init__(self, parents):
        parent_hashes = [parent.hash for parent in parents]
        assert len(parent_hashes) == len(set(parent_hashes)), 'Same node cannot be included as parent multiple times'
        self.parents = parents

    @classmethod
    def _add_operator(cls, node_class):
        if not getattr(node_class, 'STATIC', False):
            def func(self, *args, **kwargs):
                return _create_child_node(node_class, self, *args, **kwargs)
            setattr(cls, node_class.NAME, func)

    @classmethod
    def _add_operators(cls, node_classes):
        [cls._add_operator(node_class) for node_class in node_classes]

    @property
    def _props(self):
        return {k: v for k, v in self.__dict__.items() if k not in ['parents', 'hash']}

    def __repr__(self):
        # TODO: exclude default values.
        props = self._props
        formatted_props = ['{}={!r}'.format(key, props[key]) for key in sorted(self._props)]
        return '{}({})'.format(self.NAME, ','.join(formatted_props))

    def __eq__(self, other):
        return self.hash == other.hash

    def _update_hash(self):
        my_hash = hashlib.md5(json.dumps(self._props)).hexdigest()
        parent_hashes = [parent.hash for parent in self.parents]
        hashes = parent_hashes + [my_hash]
        self.hash = hashlib.md5(','.join(hashes)).hexdigest()


class _InputNode(_Node):
    pass


class _FileInputNode(_InputNode):
    NAME = 'file_input'
    STATIC = True

    def __init__(self, filename):
        super(_FileInputNode, self).__init__(parents=[])
        self.filename = filename


class _FilterNode(_Node):
    def _get_filter(self):
        raise NotImplementedError()


class _TrimNode(_FilterNode):
    NAME = 'trim'

    def __init__(self, parent, start_frame, end_frame, setpts='PTS-STARTPTS'):
        super(_TrimNode, self).__init__([parent])
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.setpts = setpts

    def _get_filter(self):
        return 'trim=start_frame={}:end_frame={},setpts={}'.format(self.start_frame, self.end_frame, self.setpts)


class _OverlayNode(_FilterNode):
    NAME = 'overlay'

    def __init__(self, main_parent, overlay_parent, eof_action='repeat'):
        super(_OverlayNode, self).__init__([main_parent, overlay_parent])
        self.eof_action = eof_action

    def _get_filter(self):
        return 'overlay=eof_action={}'.format(self.eof_action)


class _HFlipNode(_FilterNode):
    NAME = 'hflip'

    def __init__(self, parent):
        super(_HFlipNode, self).__init__([parent])

    def _get_filter(self):
        return 'hflip'


class _DrawBoxNode(_FilterNode):
    NAME = 'drawbox'

    def __init__(self, parent, x, y, width, height, color, thickness=1):
        super(_DrawBoxNode, self).__init__([parent])
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.thickness = thickness

    def _get_filter(self):
        return 'drawbox={}:{}:{}:{}:{}:t={}'.format(self.x, self.y, self.width, self.height, self.color, self.thickness)


class _ConcatNode(_Node):
    NAME = 'concat'
    STATIC = True

    def __init__(self, *parents):
        super(_ConcatNode, self).__init__(parents)

    def _get_filter(self):
        return 'concat=n={}'.format(len(self.parents))


class _OutputNode(_Node):
    @classmethod
    def _get_stream_name(cls, name):
        return '[{}]'.format(name)

    @classmethod
    def _get_input_args(cls, input_node):
        if isinstance(input_node, _FileInputNode):
            args = ['-i', input_node.filename]
        else:
            assert False, 'Unsupported input node: {}'.format(input_node)
        return args

    @classmethod
    def _topo_sort(cls, start_node):
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
                [visit(parent, node) for parent in node.parents]
                marked_nodes.remove(node)
                sorted_nodes.append(node)
        unmarked_nodes = [start_node]
        while unmarked_nodes:
            visit(unmarked_nodes.pop(), None)
        return sorted_nodes, child_map

    @classmethod
    def _get_filter_spec(cls, i, node, stream_name_map):
        stream_name = cls._get_stream_name('v{}'.format(i))
        stream_name_map[node] = stream_name
        inputs = [stream_name_map[parent] for parent in node.parents]
        filter_spec = '{}{}{}'.format(''.join(inputs), node._get_filter(), stream_name)
        return filter_spec

    @classmethod
    def _get_filter_arg(cls, filter_nodes, stream_name_map):
        filter_specs = [cls._get_filter_spec(i, node, stream_name_map) for i, node in enumerate(filter_nodes)]
        return ';'.join(filter_specs)

    @classmethod
    def _get_global_args(cls, node):
        if isinstance(node, _OverwriteOutputNode):
            return ['-y']
        else:
            assert False, 'Unsupported global node: {}'.format(node)

    @classmethod
    def _get_output_args(cls, node, stream_name_map):
        args = []
        if not isinstance(node, _MergeOutputsNode):
            stream_name = stream_name_map[node.parents[0]]
            if stream_name != '[0]':
                args += ['-map', stream_name]
            if isinstance(node, _FileOutputNode):
                args += [node.filename]
            else:
                assert False, 'Unsupported output node: {}'.format(node)
        return args

    def get_args(self):
        args = []
        # TODO: group nodes together, e.g. `-i somefile -r somerate`.
        sorted_nodes, child_map = self._topo_sort(self)
        input_nodes = [node for node in sorted_nodes if isinstance(node, _InputNode)]
        output_nodes = [node for node in sorted_nodes if isinstance(node, _OutputNode) and not
            isinstance(node, _GlobalNode)]
        global_nodes = [node for node in sorted_nodes if isinstance(node, _GlobalNode)]
        filter_nodes = [node for node in sorted_nodes if node not in (input_nodes + output_nodes + global_nodes)]
        stream_name_map = {node: self._get_stream_name(i) for i, node in enumerate(input_nodes)}
        filter_arg = self._get_filter_arg(filter_nodes, stream_name_map)
        args += reduce(operator.add, [self._get_input_args(node) for node in input_nodes])
        if filter_arg:
            args += ['-filter_complex', filter_arg]
        args += reduce(operator.add, [self._get_output_args(node, stream_name_map) for node in output_nodes])
        args += reduce(operator.add, [self._get_global_args(node) for node in global_nodes], [])
        return args

    def run(self):
        args = ['ffmpeg'] + self.get_args()
        subprocess.check_call(args)


class _GlobalNode(_OutputNode):
    def __init__(self, parent):
        assert isinstance(parent, _OutputNode), 'Global nodes can only be attached after output nodes'
        super(_GlobalNode, self).__init__([parent])


class _OverwriteOutputNode(_GlobalNode):
    NAME = 'overwrite_output'


class _MergeOutputsNode(_OutputNode):
    NAME = 'merge_outputs'
    STATIC = True

    def __init__(self, *parents):
        assert not any([not isinstance(parent, _OutputNode) for parent in parents]), 'Can only merge output streams'
        super(_MergeOutputsNode, self).__init__(*parents)


class _FileOutputNode(_OutputNode):
    NAME = 'file_output'

    def __init__(self, parent, filename):
        super(_FileOutputNode, self).__init__([parent])
        self.filename = filename


NODE_CLASSES = [
    _HFlipNode,
    _DrawBoxNode,
    _ConcatNode,
    _FileInputNode,
    _FileOutputNode,
    _OverlayNode,
    _OverwriteOutputNode,
    _TrimNode,
]

_Node._add_operators(NODE_CLASSES)

_module = sys.modules[__name__]
for _node_class in NODE_CLASSES:
    if getattr(_node_class, 'STATIC', False):
        func = _create_root_node
    else:
        func = _create_child_node
    func = partial(func, _node_class)
    setattr(_module, _node_class.NAME, func)


def get_args(node):
    assert isinstance(node, _OutputNode), 'Cannot generate ffmpeg args for non-output node'
    return node.get_args()


def run(node):
    assert isinstance(node, _OutputNode), 'Cannot run ffmpeg on non-output node'
    return node.run()
