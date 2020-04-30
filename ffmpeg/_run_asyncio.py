import asyncio

from ._run import output_operator
from ._run import *


@output_operator()
@asyncio.coroutine
def run_asyncio(
    stream_spec,
    cmd='ffmpeg',
    pipe_stdin=False,
    pipe_stdout=False,
    pipe_stderr=False,
    quiet=False,
    overwrite_output=False,
):
    """Asynchronously invoke ffmpeg in asyncio sync/await style and return coroutine.
    Have the same possibilities as `run_async` call.

    Args:
        pipe_stdin: if True, connect pipe to subprocess stdin (to be
            used with ``pipe:`` ffmpeg inputs).
        pipe_stdout: if True, connect pipe to subprocess stdout (to be
            used with ``pipe:`` ffmpeg outputs).
        pipe_stderr: if True, connect pipe to subprocess stderr.
        quiet: shorthand for setting ``capture_stdout`` and
            ``capture_stderr``.

    Returns:
        A Process instance as a coroutine
    """

    args = compile(stream_spec, cmd, overwrite_output=overwrite_output)
    stdin_stream = asyncio.subprocess.PIPE if pipe_stdin else None
    stdout_stream = asyncio.subprocess.PIPE if pipe_stdout or quiet else None
    stderr_stream = asyncio.subprocess.PIPE if pipe_stderr or quiet else None

    result = yield from asyncio.create_subprocess_exec(
        *args,
        stdin=stdin_stream,
        stdout=stdout_stream,
        stderr=stderr_stream
    )
    return result

__all__ = ['run_asyncio']
