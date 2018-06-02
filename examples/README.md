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

## [JupyterLab/Notebook widgets](https://github.com/kkroening/ffmpeg-python/blob/master/examples/ffmpeg-numpy.ipynb)

![Signal graph](https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/doc/jupyter-screenshot.png)
