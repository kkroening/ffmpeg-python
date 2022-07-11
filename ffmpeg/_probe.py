import json
import subprocess
from ._run import Error
from ._utils import convert_kwargs_to_cmd_line_args


def probe(filename, cmd='ffprobe', input=None, timeout=None, **kwargs):
    """Run ffprobe on the specified file and return a JSON representation of the output.

    Raises:
        :class:`ffmpeg.Error`: if ffprobe returns a non-zero exit code,
            an :class:`Error` is returned with a generic error message.
            The stderr output can be retrieved by accessing the
            ``stderr`` property of the exception.
    """
    args = [cmd, '-show_format', '-show_streams', '-of', 'json']
    args += convert_kwargs_to_cmd_line_args(kwargs)
    args += [filename]

    p = subprocess.Popen(
        args, stdin=None if input is None else subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate(input=input, timeout=timeout)
    if p.returncode != 0:
        raise Error('ffprobe', out, err)
    return json.loads(out.decode('utf-8'))


__all__ = ['probe']
