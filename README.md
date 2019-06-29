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

## [API reference](https://kkroening.github.io/ffmpeg-python/)

## Complex filter graphs
FFmpeg is extremely powerful, but its command-line interface gets really complicated rather quickly - especially when working with signal graphs and doing anything more than trivial.

Take for example a signal graph that looks like this:

![Signal graph](https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/doc/graph1.png)

The corresponding command-line arguments are pretty gnarly:
```bash
ffmpeg -i input.mp4 -i overlay.png -filter_complex "[0]trim=start_frame=10:end_frame=20[v0];\
    [0]trim=start_frame=30:end_frame=40[v1];[v0][v1]concat=n=2[v2];[1]hflip[v3];\
    [v2][v3]overlay=eof_action=repeat[v4];[v4]drawbox=50:50:120:120:red:t=5[v5]"\
    -map [v5] output.mp4
```

Maybe this looks great to you, but if you're not an FFmpeg command-line expert, it probably looks alien.

If you're like me and find Python to be powerful and readable, it's easier with `ffmpeg-python`:
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

`ffmpeg-python` takes care of running `ffmpeg` with the command-line arguments that correspond to the above filter diagram, in familiar Python terms.

<img src="https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/doc/screenshot.png" alt="Screenshot" align="middle" width="60%" />

Real-world signal graphs can get a heck of a lot more complex, but `ffmpeg-python` handles arbitrarily large (directed-acyclic) signal graphs.

## Installation

The latest version of `ffmpeg-python` can be acquired via a typical pip install:

```
pip install ffmpeg-python
```

Or the source can be cloned and installed from locally:
```bash
git clone git@github.com:kkroening/ffmpeg-python.git
pip install -e ./ffmpeg-python
```

## [Examples](https://github.com/kkroening/ffmpeg-python/tree/master/examples)

When in doubt, take a look at the [examples](https://github.com/kkroening/ffmpeg-python/tree/master/examples) to see if there's something that's close to whatever you're trying to do.

Here are a few:
- [Convert video to numpy array](https://github.com/kkroening/ffmpeg-python/blob/master/examples/README.md#convert-video-to-numpy-array)
- [Generate thumbnail for video](https://github.com/kkroening/ffmpeg-python/blob/master/examples/README.md#generate-thumbnail-for-video)
- [Read raw PCM audio via pipe](https://github.com/kkroening/ffmpeg-python/blob/master/examples/README.md#convert-sound-to-raw-pcm-audio)

- [JupyterLab/Notebook stream editor](https://github.com/kkroening/ffmpeg-python/blob/master/examples/README.md#jupyter-stream-editor)

<img src="https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/doc/jupyter-demo.gif" alt="jupyter demo" width="75%" />

- [Tensorflow/DeepDream streaming](https://github.com/kkroening/ffmpeg-python/blob/master/examples/README.md#tensorflow-streaming)

<img src="https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/examples/graphs/dream.png" alt="deep dream streaming" width="40%" />

See the [Examples README](https://github.com/kkroening/ffmpeg-python/tree/master/examples) for additional examples.

## Custom Filters

Don't see the filter you're looking for?  While `ffmpeg-python` includes shorthand notation for some of the most commonly used filters (such as `concat`), all filters can be referenced via the `.filter` operator:
```python
stream = ffmpeg.input('dummy.mp4')
stream = ffmpeg.filter(stream, 'fps', fps=25, round='up')
stream = ffmpeg.output(stream, 'dummy2.mp4')
ffmpeg.run(stream)
```

Or fluently:
```python
(
    ffmpeg
    .input('dummy.mp4')
    .filter('fps', fps=25, round='up')
    .output('dummy2.mp4')
    .run()
)
```

**Special option names:**

Arguments with special names such as `-qscale:v` (variable bitrate), `-b:v` (constant bitrate), etc. can be specified as a keyword-args dictionary as follows:
```python
(
    ffmpeg
    .input('in.mp4')
    .output('out.mp4', **{'qscale:v': 3})
    .run()
)
```

**Multiple inputs:**

Filters that take multiple input streams can be used by passing the input streams as an array to `ffmpeg.filter`:
```python
main = ffmpeg.input('main.mp4')
logo = ffmpeg.input('logo.png')
(
    ffmpeg
    .filter([main, logo], 'overlay', 10, 10)
    .output('out.mp4')
    .run()
)
```

**Multiple outputs:**

Filters that produce multiple outputs can be used with `.filter_multi_output`:
```python
split = (
    ffmpeg
    .input('in.mp4')
    .filter_multi_output('split')  # or `.split()`
)
(
    ffmpeg
    .concat(split[0], split[1].reverse())
    .output('out.mp4')
    .run()
)
```
(In this particular case, `.split()` is the equivalent shorthand, but the general approach works for other multi-output filters)

**String expressions:**

Expressions to be interpreted by ffmpeg can be included as string parameters and reference any special ffmpeg variable names:
```python
(
    ffmpeg
    .input('in.mp4')
    .filter('crop', 'in_w-2*10', 'in_h-2*20')
    .input('out.mp4')
)
```

<br />

When in doubt, refer to the [existing filters](https://github.com/kkroening/ffmpeg-python/blob/master/ffmpeg/_filters.py), [examples](https://github.com/kkroening/ffmpeg-python/tree/master/examples), and/or the [official ffmpeg documentation](https://ffmpeg.org/ffmpeg-filters.html).

## Frequently asked questions

**Why do I get an import/attribute/etc. error from `import ffmpeg`?**

Make sure you ran `pip install ffmpeg-python` and not `pip install ffmpeg` or `pip install python-ffmpeg`.

**Why did my audio stream get dropped?**

Some ffmpeg filters drop audio streams, and care must be taken to preserve the audio in the final output.  The ``.audio`` and ``.video`` operators can be used to reference the audio/video portions of a stream so that they can be processed separately and then re-combined later in the pipeline.

This dilemma is intrinsic to ffmpeg, and ffmpeg-python tries to stay out of the way while users may refer to the official ffmpeg documentation as to why certain filters drop audio.

As usual, take a look at the [examples](https://github.com/kkroening/ffmpeg-python/tree/master/examples#audiovideo-pipeline) (*Audio/video pipeline* in particular).

**How do I do XYZ?**

Take a look at each of the links in the [Additional Resources](https://kkroening.github.io/ffmpeg-python/) section at the end of this README.  If you look everywhere and can't find what you're looking for and have a question that may be relevant to other users, you may open an issue asking how to do it, while providing a thorough explanation of what you're trying to do and what you've tried so far.

Issues not directly related to `ffmpeg-python` or issues asking others to write your code for you or how to do the work of solving a complex signal processing problem for you that's not relevant to other users will be closed.

That said, we hope to continue improving our documentation and provide a community of support for people using `ffmpeg-python` to do cool and exciting things.

## Contributing

<img align="right" src="https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/doc/logo.png" alt="ffmpeg-python logo" width="20%" />

One of the best things you can do to help make `ffmpeg-python` better is to answer [open questions](https://github.com/kkroening/ffmpeg-python/labels/question) in the issue tracker.  The questions that are answered will be tagged and incorporated into the documentation, examples, and other learning resources.

If you notice things that could be better in the documentation or overall development experience, please say so in the [issue tracker](https://github.com/kkroening/ffmpeg-python/issues).  And of course, feel free to report any bugs or submit feature requests.

Pull requests are welcome as well, but it wouldn't hurt to touch base in the issue tracker or hop on the [Matrix chat channel](https://riot.im/app/#/room/#ffmpeg-python:matrix.org) first.

Anyone who fixes any of the [open bugs](https://github.com/kkroening/ffmpeg-python/labels/bug) or implements [requested enhancements](https://github.com/kkroening/ffmpeg-python/labels/enhancement) is a hero, but changes should include passing tests.

### Running tests

```bash
git clone git@github.com:kkroening/ffmpeg-python.git
cd ffmpeg-python
virtualenv venv
. venv/bin/activate  # (OS X / Linux)
venv\bin\activate    # (Windows)
pip install -e .[dev]
pytest
```

<br />

### Special thanks

- [Fabrice Bellard](https://bellard.org/)
- [The FFmpeg team](https://ffmpeg.org/donations.html)
- [Arne de Laat](https://github.com/153957)
- [Davide Depau](https://github.com/depau)
- [Dim](https://github.com/lloti)
- [Noah Stier](https://github.com/noahstier)

## Additional Resources

- [API Reference](https://kkroening.github.io/ffmpeg-python/)
- [Examples](https://github.com/kkroening/ffmpeg-python/tree/master/examples)
- [Filters](https://github.com/kkroening/ffmpeg-python/blob/master/ffmpeg/_filters.py)
- [FFmpeg Homepage](https://ffmpeg.org/)
- [FFmpeg Documentation](https://ffmpeg.org/ffmpeg.html)
- [FFmpeg Filters Documentation](https://ffmpeg.org/ffmpeg-filters.html)
- [Test cases](https://github.com/kkroening/ffmpeg-python/blob/master/ffmpeg/tests/test_ffmpeg.py)
- [Issue tracker](https://github.com/kkroening/ffmpeg-python/issues)
- Matrix Chat: [#ffmpeg-python:matrix.org](https://riot.im/app/#/room/#ffmpeg-python:matrix.org)
