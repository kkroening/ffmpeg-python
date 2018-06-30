# Examples

## [Get video info](https://github.com/kkroening/ffmpeg-python/blob/master/examples/video_info.py#L15)

```python
probe = ffmpeg.probe(args.in_filename)
video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
width = int(video_stream['width'])
height = int(video_stream['height'])
```

## [Convert video to numpy array](https://github.com/kkroening/ffmpeg-python/blob/master/examples/ffmpeg-numpy.ipynb)

```python
out, _ = (
    ffmpeg
    .input('in.mp4')
    .output('pipe:', format='rawvideo', pix_fmt='rgb24')
    .run(capture_stdout=True)
)
video = (
    np
    .frombuffer(out, np.uint8)
    .reshape([-1, height, width, 3])
)
```

## [Generate thumbnail for video](https://github.com/kkroening/ffmpeg-python/blob/master/examples/get_video_thumbnail.py#L21)
```python
(
    ffmpeg
    .input(in_filename, ss=time)
    .filter_('scale', width, -1)
    .output(out_filename, vframes=1)
    .run()
)
```

## [Read single video frame as jpeg through pipe](https://github.com/kkroening/ffmpeg-python/blob/master/examples/read_frame_as_jpeg.py#L16)
```python
out, _ = (
    ffmpeg
    .input(in_filename)
    .filter_('select', 'gte(n,{})'.format(frame_num))
    .output('pipe:', vframes=1, format='image2', vcodec='mjpeg')
    .run(capture_output=True)
)
```

## [Convert sound to raw PCM audio](https://github.com/kkroening/ffmpeg-python/blob/master/examples/transcribe.py#L23)
```python
out, _ = (ffmpeg
    .input(in_filename, **input_kwargs)
    .output('-', format='s16le', acodec='pcm_s16le', ac=1, ar='16k')
    .overwrite_output()
    .run(capture_stdout=True)
)
```

## Process audio and video simultaneously
```python
in1 = ffmpeg.input('in1.mp4')
in2 = ffmpeg.input('in2.mp4')
v1 = in1['v'].hflip()
a1 = in1['a']
v2 = in2['v'].filter_('reverse').filter_('hue', s=0)
a2 = in2['a'].filter_('areverse').filter_('aphaser')
joined = ffmpeg.concat(v1, a1, v2, a2, v=1, a=1).node
v3 = joined[0]
a3 = joined[1].filter_('volume', 0.8)
out = ffmpeg.output(v3, a3, 'out.mp4')
out.run()
```

## [Jupyter Frame Viewer](https://github.com/kkroening/ffmpeg-python/blob/master/examples/ffmpeg-numpy.ipynb)

<img src="https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/doc/jupyter-screenshot.png" alt="jupyter screenshot" width="75%" />

## [Jupyter Stream Editor](https://github.com/kkroening/ffmpeg-python/blob/master/examples/ffmpeg-numpy.ipynb)

<img src="https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/doc/jupyter-demo.gif" alt="jupyter demo" width="75%" />
