from __future__ import unicode_literals
from .nodes import (
    FilterNode,
    operator,
)


@operator()
def filter_(parent_node, filter_name, *args, **kwargs):
    """Apply custom single-source filter.

    ``filter_`` is normally used by higher-level filter functions such as ``hflip``, but if a filter implementation
    is missing from ``fmpeg-python``, you can call ``filter_`` directly to have ``fmpeg-python`` pass the filter name
    and arguments to ffmpeg verbatim.

    Args:
        parent_node: Source stream to apply filter to.
        filter_name: ffmpeg filter name, e.g. `colorchannelmixer`
        *args: list of args to pass to ffmpeg verbatim
        **kwargs: list of keyword-args to pass to ffmpeg verbatim

    This function is used internally by all of the other single-source filters (e.g. ``hflip``, ``crop``, etc.).
    For custom multi-source filters, see ``filter_multi`` instead.

    The function name is suffixed with ``_`` in order avoid confusion with the standard python ``filter`` function.

    Example:

        ``ffmpeg.input('in.mp4').filter_('hflip').output('out.mp4').run()``
    """
    return FilterNode([parent_node], filter_name, *args, **kwargs)


def filter_multi(parent_nodes, filter_name, *args, **kwargs):
    """Apply custom multi-source filter.

    This is nearly identical to the ``filter`` function except that it allows filters to be applied to multiple
    streams.  It's normally used by higher-level filter functions such as ``concat``, but if a filter implementation
    is missing from ``fmpeg-python``, you can call ``filter_multi`` directly.

    Note that because it applies to multiple streams, it can't be used as an operator, unlike the ``filter`` function
    (e.g. ``ffmpeg.input('in.mp4').filter_('hflip')``)

    Args:
        parent_nodes: List of source streams to apply filter to.
        filter_name: ffmpeg filter name, e.g. `concat`
        *args: list of args to pass to ffmpeg verbatim
        **kwargs: list of keyword-args to pass to ffmpeg verbatim

    For custom single-source filters, see ``filter_multi`` instead.

    Example:

        ``ffmpeg.filter_multi(ffmpeg.input('in1.mp4'), ffmpeg.input('in2.mp4'), 'concat', n=2).output('out.mp4').run()``
    """
    return FilterNode(parent_nodes, filter_name, *args, **kwargs)



@operator()
def setpts(parent_node, expr):
    """Change the PTS (presentation timestamp) of the input frames.

    Args:
        expr: The expression which is evaluated for each frame to construct its timestamp.

    Official documentation: `setpts, asetpts <https://ffmpeg.org/ffmpeg-filters.html#setpts_002c-asetpts>`__
    """
    return filter_(parent_node, setpts.__name__, expr)


@operator()
def trim(parent_node, **kwargs):
    """Trim the input so that the output contains one continuous subpart of the input.

    Args:
        start: Specify the time of the start of the kept section, i.e. the frame with the timestamp start will be the
            first frame in the output.
        end: Specify the time of the first frame that will be dropped, i.e. the frame immediately preceding the one
            with the timestamp end will be the last frame in the output.
        start_pts: This is the same as start, except this option sets the start timestamp in timebase units instead of
            seconds.
        end_pts: This is the same as end, except this option sets the end timestamp in timebase units instead of
            seconds.
        duration: The maximum duration of the output in seconds.
        start_frame: The number of the first frame that should be passed to the output.
        end_frame: The number of the first frame that should be dropped.

    Official documentation: `trim <https://ffmpeg.org/ffmpeg-filters.html#trim>`__
    """
    return filter_(parent_node, trim.__name__, **kwargs)


@operator()
def overlay(main_parent_node, overlay_parent_node, eof_action='repeat', **kwargs):
    """Overlay one video on top of another.

    Args:
        x: Set the expression for the x coordinates of the overlaid video on the main video. Default value is 0. In
            case the expression is invalid, it is set to a huge value (meaning that the overlay will not be displayed
            within the output visible area).
        y: Set the expression for the y coordinates of the overlaid video on the main video. Default value is 0. In
            case the expression is invalid, it is set to a huge value (meaning that the overlay will not be displayed
            within the output visible area).
        eof_action: The action to take when EOF is encountered on the secondary input; it accepts one of the following
            values:

            * ``repeat``: Repeat the last frame (the default).
            * ``endall``: End both streams.
            * ``pass``: Pass the main input through.

        eval: Set when the expressions for x, and y are evaluated.
            It accepts the following values:

            * ``init``: only evaluate expressions once during the filter initialization or when a command is
                processed
            * ``frame``: evaluate expressions for each incoming frame

            Default value is ``frame``.
        shortest: If set to 1, force the output to terminate when the shortest input terminates. Default value is 0.
        format: Set the format for the output video.
            It accepts the following values:

            * ``yuv420``: force YUV420 output
            * ``yuv422``: force YUV422 output
            * ``yuv444``: force YUV444 output
            * ``rgb``: force packed RGB output
            * ``gbrp``: force planar RGB output

            Default value is ``yuv420``.
        rgb (deprecated): If set to 1, force the filter to accept inputs in the RGB color space. Default value is 0.
            This option is deprecated, use format instead.
        repeatlast: If set to 1, force the filter to draw the last overlay frame over the main input until the end of
            the stream. A value of 0 disables this behavior. Default value is 1.

    Official documentation: `overlay <https://ffmpeg.org/ffmpeg-filters.html#overlay-1>`__
    """
    kwargs['eof_action'] = eof_action
    return filter_multi([main_parent_node, overlay_parent_node], overlay.__name__, **kwargs)


@operator()
def hflip(parent_node):
    """Flip the input video horizontally.

    Official documentation: `hflip <https://ffmpeg.org/ffmpeg-filters.html#hflip>`__
    """
    return filter_(parent_node, hflip.__name__)


@operator()
def vflip(parent_node):
    """Flip the input video vertically.

    Official documentation: `vflip <https://ffmpeg.org/ffmpeg-filters.html#vflip>`__
    """
    return filter_(parent_node, vflip.__name__)


@operator()
def drawbox(parent_node, x, y, width, height, color, thickness=None, **kwargs):
    """Draw a colored box on the input image.

    Args:
        x: The expression which specifies the top left corner x coordinate of the box. It defaults to 0.
        y: The expression which specifies the top left corner y coordinate of the box. It defaults to 0.
        width: Specify the width of the box; if 0 interpreted as the input width. It defaults to 0.
        heigth: Specify the height of the box; if 0 interpreted as the input height. It defaults to 0.
        color: Specify the color of the box to write. For the general syntax of this option, check the "Color" section
            in the ffmpeg-utils manual. If the special value invert is used, the box edge color is the same as the
            video with inverted luma.
        thickness: The expression which sets the thickness of the box edge. Default value is 3.
        w: Alias for ``width``.
        h: Alias for ``height``.
        c: Alias for ``color``.
        t: Alias for ``thickness``.

    Official documentation: `drawbox <https://ffmpeg.org/ffmpeg-filters.html#drawbox>`__
    """
    if thickness:
        kwargs['t'] = thickness
    return filter_(parent_node, drawbox.__name__, x, y, width, height, color, **kwargs)


@operator()
def concat(*parent_nodes, **kwargs):
    """Concatenate audio and video streams, joining them together one after the other.

    The filter works on segments of synchronized video and audio streams. All segments must have the same number of
    streams of each type, and that will also be the number of streams at output.

    Args:
        unsafe: Activate unsafe mode: do not fail if segments have a different format.

    Related streams do not always have exactly the same duration, for various reasons including codec frame size or
    sloppy authoring. For that reason, related synchronized streams (e.g. a video and its audio track) should be
    concatenated at once. The concat filter will use the duration of the longest stream in each segment (except the
    last one), and if necessary pad shorter audio streams with silence.

    For this filter to work correctly, all segments must start at timestamp 0.

    All corresponding streams must have the same parameters in all segments; the filtering system will automatically
    select a common pixel format for video streams, and a common sample format, sample rate and channel layout for
    audio streams, but other settings, such as resolution, must be converted explicitly by the user.

    Different frame rates are acceptable but will result in variable frame rate at output; be sure to configure the
    output file to handle it.

    Official documentation: `concat <https://ffmpeg.org/ffmpeg-filters.html#concat>`__
    """
    kwargs['n'] = len(parent_nodes)
    return filter_multi(parent_nodes, concat.__name__, **kwargs)


@operator()
def zoompan(parent_node, **kwargs):
    """Apply Zoom & Pan effect.

    Args:
        zoom: Set the zoom expression. Default is 1.
        x: Set the x expression. Default is 0.
        y: Set the y expression. Default is 0.
        d: Set the duration expression in number of frames. This sets for how many number of frames effect will last
            for single input image.
        s: Set the output image size, default is ``hd720``.
        fps: Set the output frame rate, default is 25.
        z: Alias for ``zoom``.

    Official documentation: `zoompan <https://ffmpeg.org/ffmpeg-filters.html#zoompan>`__
    """
    return filter_(parent_node, zoompan.__name__, **kwargs)


@operator()
def hue(parent_node, **kwargs):
    """Modify the hue and/or the saturation of the input.

    Args:
        h: Specify the hue angle as a number of degrees. It accepts an expression, and defaults to "0".
        s: Specify the saturation in the [-10,10] range. It accepts an expression and defaults to "1".
        H: Specify the hue angle as a number of radians. It accepts an expression, and defaults to "0".
        b: Specify the brightness in the [-10,10] range. It accepts an expression and defaults to "0".

    Official documentation: `hue <https://ffmpeg.org/ffmpeg-filters.html#hue>`__
    """
    return filter_(parent_node, hue.__name__, **kwargs)


@operator()
def colorchannelmixer(parent_node, *args, **kwargs):
    """Adjust video input frames by re-mixing color channels.

    Official documentation: `colorchannelmixer <https://ffmpeg.org/ffmpeg-filters.html#colorchannelmixer>`__
    """
    return filter_(parent_node, colorchannelmixer.__name__, **kwargs)


__all__ = [
    'colorchannelmixer',
    'concat',
    'drawbox',
    'filter_',
    'filter_multi',
    'hflip',
    'hue',
    'overlay',
    'setpts',
    'trim',
    'vflip',
    'zoompan',
]
