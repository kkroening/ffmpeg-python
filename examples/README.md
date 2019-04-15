# Examples

## [Get video info (ffprobe)](https://github.com/kkroening/ffmpeg-python/blob/master/examples/video_info.py#L15)

```python
probe = ffmpeg.probe(args.in_filename)
video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
width = int(video_stream['width'])
height = int(video_stream['height'])
```

## [Generate thumbnail for video](https://github.com/kkroening/ffmpeg-python/blob/master/examples/get_video_thumbnail.py#L21)

<img src="https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/examples/graphs/get_video_thumbnail.png" alt="get-video-thumbnail graph" width="30%" />

```python
(
    ffmpeg
    .input(in_filename, ss=time)
    .filter('scale', width, -1)
    .output(out_filename, vframes=1)
    .run()
)
```

## [Convert video to numpy array](https://github.com/kkroening/ffmpeg-python/blob/master/examples/ffmpeg-numpy.ipynb)

<img src="https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/examples/graphs/ffmpeg-numpy.png" alt="ffmpeg-numpy graph" width="20%" />

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

## [Read single video frame as jpeg through pipe](https://github.com/kkroening/ffmpeg-python/blob/master/examples/read_frame_as_jpeg.py#L16)

<img src="https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/examples/graphs/read_frame_as_jpeg.png" alt="read-frame-as-jpeg graph" width="30%" />

```python
out, _ = (
    ffmpeg
    .input(in_filename)
    .filter('select', 'gte(n,{})'.format(frame_num))
    .output('pipe:', vframes=1, format='image2', vcodec='mjpeg')
    .run(capture_stdout=True)
)
```

## [Convert sound to raw PCM audio](https://github.com/kkroening/ffmpeg-python/blob/master/examples/transcribe.py#L23)

<img src="https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/examples/graphs/transcribe.png" alt="transcribe graph" width="30%" />

```python
out, _ = (ffmpeg
    .input(in_filename, **input_kwargs)
    .output('-', format='s16le', acodec='pcm_s16le', ac=1, ar='16k')
    .overwrite_output()
    .run(capture_stdout=True)
)
```

## Assemble video from sequence of frames

<img src="https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/examples/graphs/glob.png" alt="glob" width="25%" />

```python
(
    ffmpeg
    .input('/path/to/jpegs/*.jpg', pattern_type='glob', framerate=25)
    .output('movie.mp4')
    .run()
)
```

With additional filtering:

<img src="https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/examples/graphs/glob-filter.png" alt="glob-filter" width="50%" />

```python
(
    ffmpeg
    .input('/path/to/jpegs/*.jpg', pattern_type='glob', framerate=25)
    .filter('deflicker', mode='pm', size=10)
    .filter('scale', size='hd1080', force_original_aspect_ratio='increase')
    .output('movie.mp4', crf=20, preset='slower', movflags='faststart', pix_fmt='yuv420p')
    .view(filename='filter_graph')
    .run()
)
```

## Audio/video pipeline

<img src="https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/examples/graphs/av-pipeline.png" alt="av-pipeline graph" width="80%" />

```python
in1 = ffmpeg.input('in1.mp4')
in2 = ffmpeg.input('in2.mp4')
v1 = in1['v'].hflip()
a1 = in1['a']
v2 = in2['v'].filter('reverse').filter('hue', s=0)
a2 = in2['a'].filter('areverse').filter('aphaser')
joined = ffmpeg.concat(v1, a1, v2, a2, v=1, a=1).node
v3 = joined[0]
a3 = joined[1].filter('volume', 0.8)
out = ffmpeg.output(v3, a3, 'out.mp4')
out.run()
```

## [Jupyter Frame Viewer](https://github.com/kkroening/ffmpeg-python/blob/master/examples/ffmpeg-numpy.ipynb)

<img src="https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/doc/jupyter-screenshot.png" alt="jupyter screenshot" width="75%" />

## [Jupyter Stream Editor](https://github.com/kkroening/ffmpeg-python/blob/master/examples/ffmpeg-numpy.ipynb)

<img src="https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/doc/jupyter-demo.gif" alt="jupyter demo" width="75%" />

## [Tensorflow Streaming](https://github.com/kkroening/ffmpeg-python/blob/master/examples/tensorflow_stream.py)

<img src="https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/examples/graphs/tensorflow-stream.png" alt="tensorflow streaming; challenge mode: combine this with the webcam example below" width="55%" />

- Decode input video with ffmpeg
- Process video with tensorflow using "deep dream" example
- Encode output video with ffmpeg

```python
process1 = (
    ffmpeg
    .input(in_filename)
    .output('pipe:', format='rawvideo', pix_fmt='rgb24', vframes=8)
    .run_async(pipe_stdout=True)
)

process2 = (
    ffmpeg
    .input('pipe:', format='rawvideo', pix_fmt='rgb24', s='{}x{}'.format(width, height))
    .output(out_filename, pix_fmt='yuv420p')
    .overwrite_output()
    .run_async(pipe_stdin=True)
)

while True:
    in_bytes = process1.stdout.read(width * height * 3)
    if not in_bytes:
        break
    in_frame = (
        np
        .frombuffer(in_bytes, np.uint8)
        .reshape([height, width, 3])
    )

    # See examples/tensorflow_stream.py:
    out_frame = deep_dream.process_frame(in_frame)

    process2.stdin.write(
        in_frame
        .astype(np.uint8)
        .tobytes()
    )

process2.stdin.close()
process1.wait()
process2.wait()
```

<img src="https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/examples/graphs/dream.png" alt="deep dream streaming" width="40%" />

## [FaceTime webcam input (OS X)](https://github.com/kkroening/ffmpeg-python/blob/master/examples/facetime.py)

```python
(
    ffmpeg
    .input('FaceTime', format='avfoundation', pix_fmt='uyvy422', framerate=30)
    .output('out.mp4', pix_fmt='yuv420p', vframes=100)
    .run()
)
```

## Stream from RTSP server to TCP socket

```python
packet_size = 4096

process = (
    ffmpeg
    .input('rtsp://%s:8554/default')
    .output('-', format='h264')
    .run_async(pipe_stdout=True)
)

while process.poll() is None:
    packet = process.stdout.read(packet_size)
    try:
        tcp_socket.send(packet)
    except socket.error:
        process.stdout.close()
        process.wait()
        break
```
