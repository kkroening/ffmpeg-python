#!./venv/bin/python

import hashlib
import json
import operator as _operator
import subprocess


class Node(object):
    def __init__(self, parents, name, *args, **kwargs):
        parent_hashes = [parent._hash for parent in parents]
        assert len(parent_hashes) == len(set(parent_hashes)), 'Same node cannot be included as parent multiple times'
        self._parents = parents
        self._name = name
        self._args = args
        self._kwargs = kwargs
        self._update_hash()

    @classmethod
    def _add_operator(cls, func):
        setattr(cls, func.__name__, func)

    def __repr__(self):
        formatted_props = ['{}'.format(arg) for arg in self._args]
        formatted_props += ['{}={!r}'.format(key, self._kwargs[key]) for key in sorted(self._kwargs)]
        return '{}({})'.format(self._name, ','.join(formatted_props))

    def __eq__(self, other):
        return self._hash == other._hash

    def _update_hash(self):
        props = {'args': self._args, 'kwargs': self._kwargs}
        my_hash = hashlib.md5(json.dumps(props, sort_keys=True)).hexdigest()
        parent_hashes = [parent._hash for parent in self._parents]
        hashes = parent_hashes + [my_hash]
        self._hash = hashlib.md5(','.join(hashes)).hexdigest()


class InputNode(Node):
    def __init__(self, name, *args, **kwargs):
        super(InputNode, self).__init__(parents=[], name=name, *args, **kwargs)


class FilterNode(Node):
    def _get_filter(self):
        params_text = self._name
        arg_params = ['{}'.format(arg) for arg in self._args]
        kwarg_params = ['{}={}'.format(k, self._kwargs[k]) for k in sorted(self._kwargs)]
        params = arg_params + kwarg_params
        if params:
            params_text += '={}'.format(':'.join(params))
        return params_text


class OutputNode(Node):
    pass


class GlobalNode(Node):
    def __init__(self, parent, name, *args, **kwargs):
        assert isinstance(parent, OutputNode), 'Global nodes can only be attached after output nodes'
        super(GlobalNode, self).__init__([parent], name, *args, **kwargs)


def operator(node_classes={Node}):
    def decorator(func):
        [node_class._add_operator(func) for node_class in node_classes]
        return func
    return decorator


def file_input(filename):
    return InputNode(file_input.__name__, filename=filename)


@operator()
def setpts(parent, expr):
    return FilterNode([parent], setpts.__name__, expr)


@operator()
def trim(parent, **kwargs):
    return FilterNode([parent], trim.__name__, **kwargs)


@operator()
def overlay(main_parent, overlay_parent, eof_action='repeat', **kwargs):
    kwargs['eof_action'] = eof_action
    return FilterNode([main_parent, overlay_parent], overlay.__name__, **kwargs)


@operator()
def hflip(parent):
    return FilterNode([parent], hflip.__name__)


@operator()
def vflip(parent):
    return FilterNode([parent], vflip.__name__)


@operator()
def drawbox(parent, x, y, width, height, color, thickness=None, **kwargs):
    if thickness:
        kwargs['t'] = thickness
    return FilterNode([parent], drawbox.__name__, x, y, width, height, color, **kwargs)


@operator()
def concat(*parents, **kwargs):
    kwargs['n'] = len(parents)
    return FilterNode(parents, concat.__name__, **kwargs)


@operator()
def zoompan(parent, **kwargs):
    return FilterNode([parent], zoompan.__name__, **kwargs)


@operator()
def hue(parent, **kwargs):
    return FilterNode([parent], hue.__name__, **kwargs)


@operator()
def colorchannelmixer(parent, *args, **kwargs):
    return FilterNode([parent], colorchannelmixer.__name__, **kwargs)


@operator(node_classes={OutputNode, GlobalNode})
def overwrite_output(parent):
    return GlobalNode(parent, overwrite_output.__name__)


@operator(node_classes={OutputNode})
def merge_outputs(*parents):
    return OutputNode(parents, merge_outputs.__name__)


@operator(node_classes={InputNode, FilterNode})
def file_output(parent, filename):
    return OutputNode([parent], file_output.__name__, filename=filename)


def _get_stream_name(name):
    return '[{}]'.format(name)


def _get_input_args(input_node):
    if input_node._name == file_input.__name__:
        args = ['-i', input_node._kwargs['filename']]
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
        if node._name == file_output.__name__:
            args += [node._kwargs['filename']]
        else:
            assert False, 'Unsupported output node: {}'.format(node)
    return args


@operator(node_classes={OutputNode, GlobalNode})
def get_args(parent):
    args = []
    # TODO: group nodes together, e.g. `-i somefile -r somerate`.
    sorted_nodes, child_map = _topo_sort(parent)
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
def run(parent, cmd='ffmpeg'):
    if type(cmd) == str:
        cmd = [cmd]
    elif type(cmd) != list:
        cmd = list(cmd)
    args = cmd + parent.get_args()
    subprocess.check_call(args)
