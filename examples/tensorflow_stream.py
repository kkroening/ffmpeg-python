'''Example streaming ffmpeg numpy processing.

Demonstrates using ffmpeg to decode video input, process the frames in
python, and then encode video output using ffmpeg.

This example uses two ffmpeg processes - one to decode the input video
and one to encode an output video - while the raw frame processing is
done in python with numpy.

At a high level, the signal graph looks like this:

  (input video) -> [ffmpeg process 1] -> [python] -> [ffmpeg process 2] -> (output video)

This example reads/writes video files on the local filesystem, but the
same pattern can be used for other kinds of input/output (e.g. webcam,
rtmp, etc.).

The simplest processing example simply darkens each frame by
multiplying the frame's numpy array by a constant value; see
``process_frame_simple``.

A more sophisticated example processes each frame with tensorflow using
the "deep dream" tensorflow tutorial; activate this mode by calling
the script with the optional `--dream` argument.  (Make sure tensorflow
is installed before running)
'''
from __future__ import print_function
import argparse
import ffmpeg
import logging
import numpy as np
import os
import subprocess
import zipfile


parser = argparse.ArgumentParser(description='Example streaming ffmpeg numpy processing')
parser.add_argument('in_filename', help='Input filename')
parser.add_argument('out_filename', help='Output filename')
parser.add_argument(
    '--dream', action='store_true', help='Use DeepDream frame processing (requires tensorflow)')

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_video_size(filename):
    logger.info('Getting video size for {!r}'.format(filename))
    probe = ffmpeg.probe(filename)
    video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    width = int(video_info['width'])
    height = int(video_info['height'])
    return width, height


def start_ffmpeg_process1(in_filename):
    logger.info('Starting ffmpeg process1')
    args = (
        ffmpeg
        .input(in_filename)
        .output('pipe:', format='rawvideo', pix_fmt='rgb24', vframes=8)
        .compile()
    )
    return subprocess.Popen(args, stdout=subprocess.PIPE)


def start_ffmpeg_process2(out_filename, width, height):
    logger.info('Starting ffmpeg process2')
    args = (
        ffmpeg
        .input('pipe:', format='rawvideo', pix_fmt='rgb24', s='{}x{}'.format(width, height))
        .output(out_filename, pix_fmt='yuv420p')
        .overwrite_output()
        .compile()
    )
    return subprocess.Popen(args, stdin=subprocess.PIPE)


def read_frame(process1, width, height):
    logger.debug('Reading frame')

    # Note: RGB24 == 3 bytes per pixel.
    frame_size = width * height * 3
    in_bytes = process1.stdout.read(frame_size)
    if len(in_bytes) == 0:
        frame = None
    else:
        assert len(in_bytes) == frame_size
        frame = (
            np
            .frombuffer(in_bytes, np.uint8)
            .reshape([height, width, 3])
        )
    return frame


def process_frame_simple(frame):
    '''Simple processing example: darken frame.'''
    return frame * 0.3


def write_frame(process2, frame):
    logger.debug('Writing frame')
    process2.stdin.write(
        frame
        .astype(np.uint8)
        .tobytes()
    )


def run(in_filename, out_filename, process_frame):
    width, height = get_video_size(in_filename)
    process1 = start_ffmpeg_process1(in_filename)
    process2 = start_ffmpeg_process2(out_filename, width, height)
    while True:
        frame = read_frame(process1, width, height)
        if frame is None:
            logger.info('End of input stream')
            break

        logger.debug('Processing frame')
        frame = process_frame(frame)
        write_frame(process2, frame)

    logger.info('Waiting for ffmpeg process1')
    process1.wait()

    logger.info('Waiting for ffmpeg process2')
    process2.stdin.close()
    process2.wait()

    logger.info('Done')


class DeepDream(object):
    '''DeepDream implementation, adapted from official tensorflow deepdream tutorial:
    https://github.com/tensorflow/tensorflow/tree/master/tensorflow/examples/tutorials/deepdream

    Credit: Alexander Mordvintsev
    '''

    _DOWNLOAD_URL = 'https://storage.googleapis.com/download.tensorflow.org/models/inception5h.zip'
    _ZIP_FILENAME = 'deepdream_model.zip'
    _MODEL_FILENAME = 'tensorflow_inception_graph.pb'

    @staticmethod
    def _download_model():
        logger.info('Downloading deepdream model...')
        try:
            from urllib.request import urlretrieve  # python 3
        except ImportError:
            from urllib import urlretrieve  # python 2
        urlretrieve(DeepDream._DOWNLOAD_URL, DeepDream._ZIP_FILENAME)

        logger.info('Extracting deepdream model...')
        zipfile.ZipFile(DeepDream._ZIP_FILENAME, 'r').extractall('.')

    @staticmethod
    def _tffunc(*argtypes):
        '''Helper that transforms TF-graph generating function into a regular one.
        See `_resize` function below.
        '''
        placeholders = list(map(tf.placeholder, argtypes))
        def wrap(f):
            out = f(*placeholders)
            def wrapper(*args, **kw):
                return out.eval(dict(zip(placeholders, args)), session=kw.get('session'))
            return wrapper
        return wrap

    @staticmethod
    def _base_resize(img, size):
        '''Helper function that uses TF to resize an image'''
        img = tf.expand_dims(img, 0)
        return tf.image.resize_bilinear(img, size)[0,:,:,:]

    def __init__(self):
        if not os.path.exists(DeepDream._MODEL_FILENAME):
            self._download_model()

        self._graph = tf.Graph()
        self._session = tf.InteractiveSession(graph=self._graph)
        self._resize = self._tffunc(np.float32, np.int32)(self._base_resize)
        with tf.gfile.FastGFile(DeepDream._MODEL_FILENAME, 'rb') as f:
            graph_def = tf.GraphDef()
            graph_def.ParseFromString(f.read())
        self._t_input = tf.placeholder(np.float32, name='input') # define the input tensor
        imagenet_mean = 117.0
        t_preprocessed = tf.expand_dims(self._t_input-imagenet_mean, 0)
        tf.import_graph_def(graph_def, {'input':t_preprocessed})

        self.t_obj = self.T('mixed4d_3x3_bottleneck_pre_relu')[:,:,:,139]
        #self.t_obj = tf.square(self.T('mixed4c'))

    def T(self, layer_name):
        '''Helper for getting layer output tensor'''
        return self._graph.get_tensor_by_name('import/%s:0'%layer_name)

    def _calc_grad_tiled(self, img, t_grad, tile_size=512):
        '''Compute the value of tensor t_grad over the image in a tiled way.
        Random shifts are applied to the image to blur tile boundaries over 
        multiple iterations.'''
        sz = tile_size
        h, w = img.shape[:2]
        sx, sy = np.random.randint(sz, size=2)
        img_shift = np.roll(np.roll(img, sx, 1), sy, 0)
        grad = np.zeros_like(img)
        for y in range(0, max(h-sz//2, sz),sz):
            for x in range(0, max(w-sz//2, sz),sz):
                sub = img_shift[y:y+sz,x:x+sz]
                g = self._session.run(t_grad, {self._t_input:sub})
                grad[y:y+sz,x:x+sz] = g
        return np.roll(np.roll(grad, -sx, 1), -sy, 0)

    def process_frame(self, frame, iter_n=10, step=1.5, octave_n=4, octave_scale=1.4):
        t_score = tf.reduce_mean(self.t_obj) # defining the optimization objective
        t_grad = tf.gradients(t_score, self._t_input)[0] # behold the power of automatic differentiation!

        # split the image into a number of octaves
        img = frame
        octaves = []
        for i in range(octave_n-1):
            hw = img.shape[:2]
            lo = self._resize(img, np.int32(np.float32(hw)/octave_scale))
            hi = img-self._resize(lo, hw)
            img = lo
            octaves.append(hi)
        
        # generate details octave by octave
        for octave in range(octave_n):
            if octave>0:
                hi = octaves[-octave]
                img = self._resize(img, hi.shape[:2])+hi
            for i in range(iter_n):
                g = self._calc_grad_tiled(img, t_grad)
                img += g*(step / (np.abs(g).mean()+1e-7))
                #print('.',end = ' ')
        return img


if __name__ == '__main__':
    args = parser.parse_args()
    if args.dream:
        import tensorflow as tf
        process_frame = DeepDream().process_frame
    else:
        process_frame = process_frame_simple
    run(args.in_filename, args.out_filename, process_frame)
