from .nodes import (
    FilterNode,
    operator,
)


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
    """Adjust video input frames by re-mixing color channels.

    `FFmpeg colorchannelmixer filter`_

    .. _FFmpeg colorchannelmixer filter:
        https://ffmpeg.org/ffmpeg-filters.html#toc-colorchannelmixer
    """
    return FilterNode([parent], colorchannelmixer.__name__, **kwargs)


__all__ = [
    'colorchannelmixer',
    'concat',
    'drawbox',
    'hflip',
    'hue',
    'overlay',
    'setpts',
    'trim',
    'vflip',
    'zoompan',
]
