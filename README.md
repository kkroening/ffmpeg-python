# ffmpeg-python: Python bindings for FFmpeg

[![Build status](https://travis-ci.org/kkroening/ffmpeg-python.svg?branch=master)](https://travis-ci.org/kkroening/ffmpeg-python)


## Overview

There are tons of Python FFmpeg wrappers out there but they seem to lack complex filter support.  `ffmpeg-python` works well for simple as well as complex signal graphs.

## Quickstart

Flip a video horizontally:
```
import ffmpeg
ffmpeg \
    .file_input('input.mp4') \
    .hflip() \
    .file_output('output.mp4') \
    .run()
```

Or if you prefer a non-fluent interface:
```
import ffmpeg
in = ffmpeg.file_input('input.mp4')
flipped = ffmpeg.hflip(in)
out = ffmpeg.file_output(flipped)
ffmpeg.run(out)
```

## Complex filter graphs
FFmpeg is extremely powerful, but its command-line interface gets really complicated really quickly - especially when working with signal graphs and doing anything more than trivial.

Take for example a signal graph that looks like this:

![Signal graph](https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/doc/graph1.png)

The corresponding command-line arguments are pretty gnarly:
```
ffmpeg -i input.mp4 \
    -vf "\
        [0]trim=start_frame=10:end_frame=20,setpts=PTS-STARTPTS[v0];\
        [0]trim=start_frame=30:end_frame=40,setpts=PTS-STARTPTS[v1];\
        [v0][v1]concat=n=2[v2];\
        [1]hflip[v3];\
        [v2][v3]overlay=eof_action=repeat[v4];\
        [v4]drawbox=50:50:120:120:red:t=5[v5]"\
     -map [v5] output.mp4
```

Maybe this looks great to you, but if you're not an FFmpeg command-line expert, it probably looks pretty alien.

If you're like me and find Python to be powerful and readable, it's easy with `ffmpeg-python`:
```
import ffmpeg

in_file = ffmpeg.file_input('input.mp4')
overlay_file = ffmpeg.file_input('overlay.png')
ffmpeg \
    .concat(
        in_file.trim(10, 20),
        in_file.trim(30, 40),
    ) \
    .overlay(overlay_file.hflip()) \
    .drawbox(50, 50, 120, 120, color='red', thickness=5) \
    .file_output(TEST_OUTPUT_FILE) \
    .run()
```

`ffmpeg-python` takes care of running `ffmpeg` with the command-line arguments that correspond to the above filter diagram, and it's easy to what's going on and make changes as needed.

<img src="https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/doc/screenshot.png" alt="Screenshot" align="middle" width="60%" />

Real-world signal graphs can get a heck of a lot more complex, but `ffmpeg-python` handles them with ease.

