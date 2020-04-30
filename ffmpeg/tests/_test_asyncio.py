import ffmpeg
import asyncio

from .test_ffmpeg import TEST_INPUT_FILE1


def test_run_asyncio():
    @asyncio.coroutine
    def test_async():
        process = yield from (
            ffmpeg
             .input(TEST_INPUT_FILE1)
             .output('pipe:', format='rawvideo', pix_fmt='rgb24')['v']
             .run_asyncio(pipe_stdout=True, quiet=False)
        )

        video_frame_size = 320 * 240 * 3  # Note: RGB24 == 3 bytes per pixel. 320x240 - video size

        total_bytes = 0

        while True:
            frame_bytes = yield from process.stdout.read(video_frame_size)
            if len(frame_bytes) == 0:
                break
            else:
                total_bytes += len(frame_bytes)

        yield from process.wait()

        assert total_bytes == 48153600, 'Incorrect size of the output frames'

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_async())
