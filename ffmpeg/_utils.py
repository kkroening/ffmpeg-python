from __future__ import unicode_literals
from builtins import str
from past.builtins import basestring
import hashlib
import sys
import collections


if sys.version_info.major == 2:
    # noinspection PyUnresolvedReferences,PyShadowingBuiltins
    str = str


# `past.builtins.basestring` module can't be imported on Python3 in some environments (Ubuntu).
# This code is copy-pasted from it to avoid crashes.
class BaseBaseString(type):
    def __instancecheck__(cls, instance):
        return isinstance(instance, (bytes, str))

    def __subclasshook__(cls, thing):
        # TODO: What should go here?
        raise NotImplemented


def with_metaclass(meta, *bases):
    class metaclass(meta):
        __call__ = type.__call__
        __init__ = type.__init__

        def __new__(cls, name, this_bases, d):
            if this_bases is None:
                return type.__new__(cls, name, (), d)
            return meta(name, bases, d)

    return metaclass('temporary_class', None, {})


if sys.version_info.major >= 3:

    class basestring(with_metaclass(BaseBaseString)):
        pass


else:
    # noinspection PyUnresolvedReferences,PyCompatibility
    from builtins import basestring


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
        kv_pairs = [
            '{}: {}'.format(_recursive_repr(k), _recursive_repr(item[k]))
            for k in sorted(item)
        ]
        result = '{' + ', '.join(kv_pairs) + '}'
    else:
        result = repr(item)
    return result


def get_hash(item):
    repr_ = _recursive_repr(item).encode('utf-8')
    return hashlib.md5(repr_).hexdigest()


def get_hash_int(item):
    return int(get_hash(item), base=16)


def escape_chars(text, chars):
    """Helper function to escape uncomfortable characters."""
    text = str(text)
    chars = list(set(chars))
    if '\\' in chars:
        chars.remove('\\')
        chars.insert(0, '\\')
    for ch in chars:
        text = text.replace(ch, '\\' + ch)
    return text


def convert_kwargs_to_cmd_line_args(kwargs):
    """Helper function to build command line arguments out of dict."""
    args = []
    for k in sorted(kwargs.keys()):
        v = kwargs[k]
        if isinstance(v, collections.Iterable) and not isinstance(v, str):
            for value in v:
                args.append('-{}'.format(k))
                if value is not None:
                    args.append('{}'.format(value))
            continue
        args.append('-{}'.format(k))
        if v is not None:
            args.append('{}'.format(v))
    return args
