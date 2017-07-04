from __future__ import unicode_literals

from builtins import object
import copy
import hashlib


def _recursive_repr(item):
    """Hack around python `repr` to deterministically represent dictionaries.

    This is able to represent more things than json.dumps, since it does not require things to be JSON serializable
    (e.g. datetimes).
    """
    if isinstance(item, basestring):
        result = str(item)
    elif isinstance(item, list):
        result = '[{}]'.format(', '.join([_recursive_repr(x) for x in item]))
    elif isinstance(item, dict):
        kv_pairs = ['{}: {}'.format(_recursive_repr(k), _recursive_repr(item[k])) for k in sorted(item)]
        result = '{' + ', '.join(kv_pairs) + '}'
    else:
        result = repr(item)
    return result


def _create_hash(item):
    hasher = hashlib.sha224()
    repr_ = _recursive_repr(item)
    hasher.update(repr_.encode('utf-8'))
    return hasher.hexdigest()


class _NodeBase(object):
    @property
    def hash(self):
        if self._hash is None:
            self._update_hash()
        return self._hash

    def __init__(self, parents, name):
        parent_hashes = [hash(parent) for parent in parents]
        assert len(parent_hashes) == len(set(parent_hashes)), 'Same node cannot be included as parent multiple times'
        self._parents = parents
        self._hash = None
        self._name = name

    def _transplant(self, new_parents):
        other = copy.copy(self)
        other._parents = copy.copy(new_parents)
        return other

    @property
    def _repr_args(self):
        raise NotImplementedError()

    @property
    def _repr_kwargs(self):
        raise NotImplementedError()

    @property
    def _short_hash(self):
        return '{:x}'.format(abs(hash(self)))[:12]

    def __repr__(self):
        args = self._repr_args
        kwargs = self._repr_kwargs
        formatted_props = ['{!r}'.format(arg) for arg in args]
        formatted_props += ['{}={!r}'.format(key, kwargs[key]) for key in sorted(kwargs)]
        return '{}({}) <{}>'.format(self._name, ', '.join(formatted_props), self._short_hash)

    def __hash__(self):
        if self._hash is None:
            self._update_hash()
        return self._hash

    def __eq__(self, other):
        return hash(self) == hash(other)

    def _update_hash(self):
        props = {'args': self._repr_args, 'kwargs': self._repr_kwargs}
        my_hash = _create_hash(props)
        parent_hashes = [str(hash(parent)) for parent in self._parents]
        hashes = parent_hashes + [my_hash]
        hashes_str = ','.join(hashes).encode('utf-8')
        hash_str = hashlib.md5(hashes_str).hexdigest()
        self._hash = int(hash_str, base=16)


class Node(_NodeBase):
    """Node base"""
    def __init__(self, parents, name, *args, **kwargs):
        super(Node, self).__init__(parents, name)
        self._args = args
        self._kwargs = kwargs

    @property
    def _repr_args(self):
        return self._args

    @property
    def _repr_kwargs(self):
        return self._kwargs


class InputNode(Node):
    """InputNode type"""
    def __init__(self, name, *args, **kwargs):
        super(InputNode, self).__init__(parents=[], name=name, *args, **kwargs)


class FilterNode(Node):
    """FilterNode"""
    def _get_filter(self):
        params_text = self._name
        arg_params = ['{}'.format(arg) for arg in self._args]
        kwarg_params = ['{}={}'.format(k, self._kwargs[k]) for k in sorted(self._kwargs)]
        params = arg_params + kwarg_params
        if params:
            params_text += '={}'.format(':'.join(params))
        return params_text


class OutputNode(Node):
    """OutputNode"""
    pass


class GlobalNode(Node):
    def __init__(self, parent, name, *args, **kwargs):
        assert isinstance(parent, OutputNode), 'Global nodes can only be attached after output nodes'
        super(GlobalNode, self).__init__([parent], name, *args, **kwargs)


def operator(node_classes={Node}, name=None):
    def decorator(func):
        func_name = name or func.__name__
        [setattr(node_class, func_name, func) for node_class in node_classes]
        return func
    return decorator
