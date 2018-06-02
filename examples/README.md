# Examples

## [Get video info](https://github.com/kkroening/ffmpeg-python/blob/master/examples/video_info.py)

```python
probe = ffmpeg.probe(args.in_filename)
video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
width = int(video_stream['width'])
height = int(video_stream['height'])
```
