# ffmpeg-python: Python bindings for FFmpeg

[![Build status](https://travis-ci.org/kkroening/ffmpeg-python.svg?branch=master)](https://travis-ci.org/kkroening/ffmpeg-python)

<img src="https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/doc/formula.png" alt="ffmpeg-python logo" width="60%" />

## Overview

There are tons of Python FFmpeg wrappers out there but they seem to lack complex filter support.  `ffmpeg-python` works well for simple as well as complex signal graphs.


## Quickstart

Flip a video horizontally:
```python
import ffmpeg
stream = ffmpeg.input('input.mp4')
stream = ffmpeg.hflip(stream)
stream = ffmpeg.output(stream, 'output.mp4')
ffmpeg.run(stream)
```

Or if you prefer a fluent interface:
```python
import ffmpeg
(
    ffmpeg
    .input('input.mp4')
    .hflip()
    .output('output.mp4')
    .run()
)
```

## Complex filter graphs
FFmpeg is extremely powerful, but its command-line interface gets really complicated really quickly - especially when working with signal graphs and doing anything more than trivial.

Take for example a signal graph that looks like this:

![Signal graph](https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/doc/graph1.png)

The corresponding command-line arguments are pretty gnarly:
```bash
ffmpeg -i input.mp4 -filter_complex "[0]trim=start_frame=10:end_frame=20[v0];\
    [0]trim=start_frame=30:end_frame=40[v1];[v0][v1]concat=n=2[v2];[1]hflip[v3];\
    [v2][v3]overlay=eof_action=repeat[v4];[v4]drawbox=50:50:120:120:red:t=5[v5]"\
    -map [v5] output.mp4
```

Maybe this looks great to you, but if you're not an FFmpeg command-line expert, it probably looks alien.

If you're like me and find Python to be powerful and readable, it's easy with `ffmpeg-python`:
```python
import ffmpeg

in_file = ffmpeg.input('input.mp4')
overlay_file = ffmpeg.input('overlay.png')
(
    ffmpeg
    .concat(
        in_file.trim(start_frame=10, end_frame=20),
        in_file.trim(start_frame=30, end_frame=40),
    )
    .overlay(overlay_file.hflip())
    .drawbox(50, 50, 120, 120, color='red', thickness=5)
    .output('out.mp4')
    .run()
)
```

`ffmpeg-python` takes care of running `ffmpeg` with the command-line arguments that correspond to the above filter diagram, and it's easy to see what's going on and make changes as needed.

<img src="https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/doc/screenshot.png" alt="Screenshot" align="middle" width="60%" />

Real-world signal graphs can get a heck of a lot more complex, but `ffmpeg-python` handles them with ease.


## Installation

The latest version of `ffmpeg-python` can be acquired via pip:

```
pip install ffmpeg-python
```

It's also possible to clone the source and put it on your python path (`$PYTHONPATH`, `sys.path`, etc.):

```bash
$ git clone git@github.com:kkroening/ffmpeg-python.git
$ export PYTHONPATH=${PYTHONPATH}:ffmpeg-python
$ python
>>> import ffmpeg
```

## [Examples](https://github.com/kkroening/ffmpeg-python/tree/master/examples)

When in doubt, take a look at the [examples](https://github.com/kkroening/ffmpeg-python/tree/master/examples) to see if there's something that's close to whatever you're trying to do.

Here are a few:
- [Convert video to numpy array](https://github.com/kkroening/ffmpeg-python/blob/master/examples/README.md#convert-video-to-numpy-array)
- [Generate thumbnail for video](https://github.com/kkroening/ffmpeg-python/blob/master/examples/README.md#generate-thumbnail-for-video)
- [Read raw PCM audio via pipe](https://github.com/kkroening/ffmpeg-python/blob/master/examples/README.md#convert-sound-to-raw-pcm-audio)
- [JupyterLab/Notebook stream editor](https://github.com/kkroening/ffmpeg-python/blob/master/examples/README.md#jupyter-stream-editor)

<img src="https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/doc/jupyter-demo.gif" alt="jupyter demo" width="75%" />

See the [Examples README](https://github.com/kkroening/ffmpeg-python/tree/master/examples) for additional examples.

## [API Reference](https://kkroening.github.io/ffmpeg-python/)

API documentation is automatically generated from python docstrings and hosted on github pages: https://kkroening.github.io/ffmpeg-python/

Alternatively, standard python help is available, such as at the python REPL prompt as follows:

```python
>>> import ffmpeg
>>> help(ffmpeg)
```

## Custom Filters

Don't see the filter you're looking for?  `ffmpeg-python` includes shorthand notation for some of the most commonly used filters (such as `concat`), but it's easy to use any arbitrary ffmpeg filter:
```python
stream = ffmpeg.input('dummy.mp4')
stream = ffmpeg.filter_(stream, 'fps', fps=25, round='up')
stream = ffmpeg.output(stream, 'dummy2.mp4')
ffmpeg.run(stream)
```

Or fluently:
```python
(
    ffmpeg
    .input('dummy.mp4')
    .filter_('fps', fps=25, round='up')
    .output('dummy2.mp4')
    .run()
)
```

Arguments with special names such as `-qscale:v` can be specified as a keyword-args dictionary as follows:
```python
(
    ffmpeg
    .input('dummy.mp4')
    .output('dummy2.mp4', **{'qscale:v': 3})
    .run()
)
```

When in doubt, refer to the [existing filters](https://github.com/kkroening/ffmpeg-python/blob/master/ffmpeg/_filters.py), [examples](https://github.com/kkroening/ffmpeg-python/tree/master/examples), and/or the [official ffmpeg documentation](https://ffmpeg.org/ffmpeg-filters.html).

## Contributing

<img align="right" src="https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/doc/logo.png" alt="ffmpeg-python logo" width="20%" />

Feel free to report any bugs or submit feature requests.

It's generally straightforward to use filters that aren't explicitly built into `ffmpeg-python` but if there's a feature you'd like to see included in the library, head over to the [issue tracker](https://github.com/kkroening/ffmpeg-python/issues).

Pull requests are welcome as well.

<br />

### Special thanks

- [Arne de Laat](https://github.com/153957)
- [Davide Depau](https://github.com/depau)
- [Dim](https://github.com/lloti)
- [Noah Stier](https://github.com/noahstier)

## Additional Resources

- [API Reference](https://kkroening.github.io/ffmpeg-python/)
- [Filters](https://github.com/kkroening/ffmpeg-python/blob/master/ffmpeg/_filters.py)
- [Tests](https://github.com/kkroening/ffmpeg-python/blob/master/ffmpeg/tests/test_ffmpeg.py)
- [FFmpeg Homepage](https://ffmpeg.org/)
- [FFmpeg Documentation](https://ffmpeg.org/ffmpeg.html)
- [FFmpeg Filters Documentation](https://ffmpeg.org/ffmpeg-filters.html)
- Matrix Chat: [#ffmpeg-python:matrix.org](https://riot.im/app/#/room/#ffmpeg-python:matrix.org)
