#!/usr/bin/env python3

# Example program for validating video

import os 
import sys 
import ffmpeg
from time import time, strftime, sleep, gmtime
import argparse
import textwrap
from datetime import datetime
from shutil import get_terminal_size

# Program Description Variables
__author__ = "Colin Bitterfield"
__copyright__ = "Copyright 2019, " 
__credits__ = ["Colin Bitterfield"]
__license__ = "GPL3"
__version__ = "0.1.0"
__maintainer__ = "colin_bitterfield"
__status__ = "example"
__created___ = "12/21/2019"
__updated___ = ""
__prog_name__ = os.path.basename(__file__)
__short_name__ = os.path.splitext(__prog_name__)[0]
__timestamp__ = time() 
__run_datetime__ = datetime.fromtimestamp(__timestamp__) # Today's Date
__console_size__ = get_terminal_size((80, 20))[0]



parser = argparse.ArgumentParser(description=textwrap.dedent('''\
    Test a video for corruption.
    Demonstrates with and without GPU/Cuda acceleration
'''.format()))
parser.prog = __prog_name__
parser.epilog = """

Written by {author} --
Copyright  {copyright} --
License    {license}
""".format(author=__author__,copyright=__copyright__,license=__license__)
parser.add_argument('--version', action='version', version=('%(prog)s ' + __version__))
parser.add_argument('-i','--in_filename', 
                    action   = 'store',
                    dest     = 'in_file',
                    required = True,
                    help     = 'Input filename')

parser.add_argument('-c', '--cuda',
                    action   = 'store_true',
                    dest     = 'use_cuda',
                    required = False,
                    default  = False,
                    help='Enable Cuda HW Acceleration')

parser.add_argument('-ff', '--ffmpeg',
                    action   = 'store',
                    dest     = 'FFMPEG',
                    required = False,
                    default  = '/usr/local/bin/ffmpeg',
                    help='ffmpeg location, defaults to /usr/local/bin/ffmpeg')


def validate_video(filename,**kwargs):
    ''' validate a video file 
    
    params:
    ---------------------------------
    filename to check (fully qualified)
    ** kargs to pass to input side of ffmpeg
    
    
    cli: ffmpeg -hide_banner -err_detect compliant -loglevel error 
    
    returns [True/False], message_of_errors
    
    example with cuda accelerator
    
    **kwargs
    {
    'hwaccel' : 'cuda',
    'vcodec'  : 'h264_cuvid'
    }
    
    validate_video(filename, **{
    'hwaccel' : 'cuda',
    'vcodec'  : 'h264_cuvid'
    })
    
    '''
    
    videoIsValid=True
    message = {}
    threads = 1
    input_arguments = {
        'hide_banner' : None, 
                    'err_detect':'compliant' ,
                    'loglevel'  : 'error'
                    }
    
    stdout,stderr = (
        ffmpeg.input(filename,**input_arguments)
        .output('pipe:', format="null")
        .overwrite_output()
        .run(cmd=FFMPEG,capture_stdout=True,capture_stderr=True )
    )
    
    
    
    if 'error' in str(stderr).lower():
        message = stderr
        videoIsValid=False
    else:
        message = 'Valid Video'
        

    return videoIsValid,message

if __name__ == '__main__':
    args = parser.parse_args()
    FFMPEG   = args.FFMPEG
    useCuda  = args.use_cuda
    filename = args.in_file
    
    print('{prog} started on {time}'.format(prog=__prog_name__,time=__run_datetime__))
    
    hw_accel = dict({
        'hwaccel' : 'cuda',
        'vcodec'  : 'h264_cuvid' 
        })
    
    if os.path.isfile(filename):
        print('Testing file {file}'.format(file=filename))
        start_time = time()
        if useCuda:
            print('Using Hardware Acceleration by Cuda')
            isValid, message = validate_video(filename,**hw_accel)
            
        else:
            isValid, message = validate_video(filename)
        
        sleep(10)
        end_time   = time() 
        run_time   = gmtime(end_time - start_time)
        strftime("%M:%S", run_time)
        print('Elapsed Time: {elapsed}'.format(elapsed=strftime("%M:%S", run_time)))
        if isValid:
            print('Video is valid and without errors')
        else:
            print('Video has errors')
            print('-' * __console_size__)
            for line in message.strip().decode().splitlines():
                print('   {}'.format(line))

    else:
        print('Filename {file} is not present on the system'.format(file=filename))