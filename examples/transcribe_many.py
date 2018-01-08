#!/usr/bin/env python
from functools import partial
from multiprocessing import Pool
from transcribe import transcribe_to_file
import argparse
import os
import logging


logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__file__)

DEFAULT_WORKER_COUNT = 20

parser = argparse.ArgumentParser(description='Transcribe multiple audio files in parallel using Google Speech API')
parser.add_argument('in_filenames', nargs='+', help='Input filename(s)')
parser.add_argument('--keep-suffix', action='store_true',
    help='Don\'t strip filename suffix when generating metadata .json output filename')
parser.add_argument('--workers', default=DEFAULT_WORKER_COUNT,
    help='Number of workers (default {})'.format(DEFAULT_WORKER_COUNT))


def transcribe_one(in_filename, keep_suffix=False):
    if keep_suffix:
        base_filename = in_filename
    else:
        base_filename = os.path.splitext(in_filename)[0]
    out_filename = '{}.json'.format(base_filename)
    logger.info('Starting: {} -> {}'.format(in_filename, out_filename))
    with open(out_filename, 'w') as out_file:
        transcribe_to_file(in_filename, out_file, as_json=True)
    logger.info('Finished: {} -> {}'.format(in_filename, out_filename))


def transcribe_many(in_filenames, keep_suffix=False, worker_count=DEFAULT_WORKER_COUNT):
    pool = Pool(processes=worker_count)
    func = partial(transcribe_one, keep_suffix=keep_suffix)
    pool.map_async(func, in_filenames).get(99999999)


if __name__ == '__main__':
    args = parser.parse_args()
    transcribe_many(args.in_filenames, args.keep_suffix)
