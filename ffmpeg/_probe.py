import json
import subprocess


class ProbeException(Exception):
    def __init__(self, stderr_output):
        super(ProbeException, self).__init__('ffprobe error')
        self.stderr_output = stderr_output


def probe(filename):
    """Run ffprobe on the specified file and return a JSON representation of the output.

    Raises:
        ProbeException: if ffprobe returns a non-zero exit code, a ``ProbeException`` is returned with a generic error
            message.  The stderr output can be retrieved by accessing the ``stderr_output`` property of the exception.
    """
    args = ['ffprobe', '-show_format', '-show_streams', '-of', 'json', filename]
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        raise ProbeException(err)
    return json.loads(out.decode('utf-8'))


__all__ = [
    'probe',
    'ProbeException',
]
