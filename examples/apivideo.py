#!/usr/bin/env python

# Use ffmpeg-python with api.video. Api.video lets you create your own live streams. 
# Complete tutorial for using ffmpeg-python with api.video here: https://api.video/blog/tutorials/live-stream-to-the-browser-with-ffmpeg-cli-and-python
# You need to get your api.video stream key and replace 'apivideo_stream_key.'
# You can probably use this for other tools as well. 

import ffmpeg

rtmp_url = 'rtmp://broadcast.api.video/s/' + 'apivideo_stream_key'

(
  ffmpeg
  .input('0:0', format='avfoundation', framerate=25)
  .output(rtmp_url, format='flv', flvflags='no_duration_filesize')
  .run()
)
