from __future__ import unicode_literals

from builtins import str
from past.builtins import basestring
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


def get_hash(item):
    repr_ = _recursive_repr(item).encode('utf-8')
    return hashlib.md5(repr_).hexdigest()

def get_hash_int(item):
    return int(get_hash(item), base=16)
