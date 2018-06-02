#!/usr/bin/env python
from __future__ import unicode_literals, print_function
from tqdm import tqdm
import argparse
import contextlib
import ffmpeg
import gevent
import gevent.monkey; gevent.monkey.patch_all(thread=False)
import os
import shutil
import socket
import sys
import tempfile
import textwrap


parser = argparse.ArgumentParser(description=textwrap.dedent('''\
    Process video and report and show progress bar.

    This is an example of using the ffmpeg `-progress` option with a
    unix-domain socket to report progress in the form of a progress
    bar.

    The video processing simply consists of converting the video to
    sepia colors, but the same pattern can be applied to other use
    cases.
'''))

parser.add_argument('in_filename', help='Input filename')
parser.add_argument('out_filename', help='Output filename')


@contextlib.contextmanager
def _tmpdir_scope():
    tmpdir = tempfile.mkdtemp()
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir)


def _do_watch_progress(filename, sock, handler):
    """Function to run in a separate gevent greenlet to read progress
    events from a unix-domain socket."""
    connection, client_address = sock.accept()
    data = b''
    try:
        while True:
            more_data = connection.recv(16)
            if not more_data:
                break
            data += more_data
            lines = data.split(b'\n')
            for line in lines[:-1]:
                line = line.decode()
                parts = line.split('=')
                key = parts[0] if len(parts) > 0 else None
                value = parts[1] if len(parts) > 1 else None
                handler(key, value)
            data = lines[-1]
    finally:
        connection.close()


@contextlib.contextmanager
def _watch_progress(handler):
    """Context manager for creating a unix-domain socket and listen for
    ffmpeg progress events.

    The socket filename is yielded from the context manager and the
    socket is closed when the context manager is exited.

    Args:
        handler: a function to be called when progress events are
            received; receives a ``key`` argument and ``value``
            argument. (The example ``show_progress`` below uses tqdm)

    Yields:
        socket_filename: the name of the socket file.
    """
    with _tmpdir_scope() as tmpdir:
        socket_filename = os.path.join(tmpdir, 'sock')
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        with contextlib.closing(sock):
            sock.bind(socket_filename)
            sock.listen(1)
            child = gevent.spawn(_do_watch_progress, socket_filename, sock, handler)
            try:
                yield socket_filename
            except:
                gevent.kill(child)
                raise



@contextlib.contextmanager
def show_progress(total_duration):
    """Create a unix-domain socket to watch progress and render tqdm
    progress bar."""
    with tqdm(total=round(total_duration, 2)) as bar:
        def handler(key, value):
            if key == 'out_time_ms':
                time = round(float(value) / 1000000., 2)
                bar.update(time - bar.n)
            elif key == 'progress' and value == 'end':
                bar.update(bar.total - bar.n)
        with _watch_progress(handler) as socket_filename:
            yield socket_filename


if __name__ == '__main__':
    args = parser.parse_args()
    total_duration = float(ffmpeg.probe(args.in_filename)['format']['duration'])

    with show_progress(total_duration) as socket_filename:
        # See https://ffmpeg.org/ffmpeg-filters.html#Examples-44
        sepia_values = [.393, .769, .189, 0, .349, .686, .168, 0, .272, .534, .131]
        try:
            (ffmpeg
                .input(args.in_filename)
                .colorchannelmixer(*sepia_values)
                .output(args.out_filename)
                .global_args('-progress', 'unix://{}'.format(socket_filename))
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
        except ffmpeg.Error as e:
            print(e.stderr, file=sys.stderr)
            sys.exit(1)

