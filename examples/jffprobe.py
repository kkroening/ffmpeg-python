#!/usr/bin/env python
import argparse
import json
import logging
import subprocess
import sys


parser = argparse.ArgumentParser(description='Run ffprobe on one or more files with JSON output')
parser.add_argument('filenames', nargs='+', help='Filename(s)')


class ExecException(Exception):
    def __init__(self, stderr_output):
        super(ExecException, self).__init__('Execution error')
        self.stderr_output = stderr_output


def run_ffprobe(filename):
    args = ['ffprobe', '-show_format', '-show_streams', '-of', 'json', filename]
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        raise ExecException(err)
    return json.loads(out)


def main(filenames):
    failed = False
    results = {}
    for filename in sys.argv[1:]:
        try:
            results[filename] = run_ffprobe(filename)
        except ExecException as e:
            logging.error('Error processing {}:'.format(filename))
            logging.error(e.stderr_output)
            failed = True
        except Exception as e:
            logging.exception('Error processing {}:'.format(filename))
            failed = True
    if results != {}:
        print(json.dumps(results, indent=4, sort_keys=True))
        if failed:
            logging.warning('One or more ffprobe calls failed. See above for detail.')
    sys.exit(int(failed))


if __name__ == '__main__':
    args = parser.parse_args()
    main(args.filenames)
