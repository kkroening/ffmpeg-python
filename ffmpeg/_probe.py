"""
Run ffprobe on the file and return a JSON representation of the output.
"""

import collections
import json
import subprocess
from ._run import Error
from ._utils import convert_kwargs_to_cmd_line_args


def probe(filename, cmd='ffprobe', **kwargs):
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
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True)
    out, err = p.communicate()
    if p.returncode != 0:
        raise Error('ffprobe', out, err)
    return json.loads(out, object_pairs_hook=collections.OrderedDict)


__all__ = ['probe']
