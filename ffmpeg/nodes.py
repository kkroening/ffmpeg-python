from __future__ import unicode_literals

from .dag import KwargReprNode


class Node(KwargReprNode):
    """Node base"""
    def __init__(self, parents, name, *args, **kwargs):
        incoming_edge_map = {}
        for downstream_label, parent in enumerate(parents):
            upstream_label = 0  # assume nodes have a single output (FIXME)
            upstream_node = parent
            incoming_edge_map[downstream_label] = (upstream_node, upstream_label)
        super(Node, self).__init__(incoming_edge_map, name, args, kwargs)

    @property
    def _parents(self):
        # TODO: change graph compilation to use `self.incoming_edges` instead.
        return [edge.upstream_node for edge in self.incoming_edges]


class InputNode(Node):
    """InputNode type"""
    def __init__(self, name, *args, **kwargs):
        super(InputNode, self).__init__(parents=[], name=name, *args, **kwargs)


class FilterNode(Node):
    """FilterNode"""
    def _get_filter(self):
        params_text = self.name
        arg_params = ['{}'.format(arg) for arg in self.args]
        kwarg_params = ['{}={}'.format(k, self.kwargs[k]) for k in sorted(self.kwargs)]
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
