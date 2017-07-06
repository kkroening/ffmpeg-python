from __future__ import unicode_literals
import ffmpeg
import os
import pytest
import subprocess
import random


TEST_DIR = os.path.dirname(__file__)
SAMPLE_DATA_DIR = os.path.join(TEST_DIR, 'sample_data')
TEST_INPUT_FILE = os.path.join(SAMPLE_DATA_DIR, 'dummy.mp4')
TEST_OVERLAY_FILE = os.path.join(SAMPLE_DATA_DIR, 'overlay.png')
TEST_OUTPUT_FILE = os.path.join(SAMPLE_DATA_DIR, 'dummy2.mp4')


subprocess.check_call(['ffmpeg', '-version'])


def test_fluent_equality():
    base1 = ffmpeg.input('dummy1.mp4')
    base2 = ffmpeg.input('dummy1.mp4')
    base3 = ffmpeg.input('dummy2.mp4')
    t1 = base1.trim(start_frame=10, end_frame=20)
    t2 = base1.trim(start_frame=10, end_frame=20)
    t3 = base1.trim(start_frame=10, end_frame=30)
    t4 = base2.trim(start_frame=10, end_frame=20)
    t5 = base3.trim(start_frame=10, end_frame=20)
    assert t1 == t2
    assert t1 != t3
    assert t1 == t4
    assert t1 != t5


def test_fluent_concat():
    base = ffmpeg.input('dummy.mp4')
    trimmed1 = base.trim(start_frame=10, end_frame=20)
    trimmed2 = base.trim(start_frame=30, end_frame=40)
    trimmed3 = base.trim(start_frame=50, end_frame=60)
    concat1 = ffmpeg.concat(trimmed1, trimmed2, trimmed3)
    concat2 = ffmpeg.concat(trimmed1, trimmed2, trimmed3)
    concat3 = ffmpeg.concat(trimmed1, trimmed3, trimmed2)
    assert concat1 == concat2
    assert concat1 != concat3


def test_fluent_output():
    (ffmpeg
        .input('dummy.mp4')
        .trim(start_frame=10, end_frame=20)
        .output('dummy2.mp4')
    )


def test_fluent_complex_filter():
    in_file = ffmpeg.input('dummy.mp4')
    return (ffmpeg
        .concat(
            in_file.trim(start_frame=10, end_frame=20),
            in_file.trim(start_frame=30, end_frame=40),
            in_file.trim(start_frame=50, end_frame=60)
        )
        .output('dummy2.mp4')
    )


def test_node_repr():
    in_file = ffmpeg.input('dummy.mp4')
    trim1 = ffmpeg.trim(in_file, start_frame=10, end_frame=20)
    trim2 = ffmpeg.trim(in_file, start_frame=30, end_frame=40)
    trim3 = ffmpeg.trim(in_file, start_frame=50, end_frame=60)
    concatted = ffmpeg.concat(trim1, trim2, trim3)
    output = ffmpeg.output(concatted, 'dummy2.mp4')
    assert repr(in_file.node) == "input(filename={!r}) <{}>".format('dummy.mp4', in_file.node.short_hash)
    assert repr(trim1.node) == "trim(end_frame=20, start_frame=10) <{}>".format(trim1.node.short_hash)
    assert repr(trim2.node) == "trim(end_frame=40, start_frame=30) <{}>".format(trim2.node.short_hash)
    assert repr(trim3.node) == "trim(end_frame=60, start_frame=50) <{}>".format(trim3.node.short_hash)
    assert repr(concatted.node) == "concat(n=3) <{}>".format(concatted.node.short_hash)
    assert repr(output.node) == "output(filename={!r}) <{}>".format('dummy2.mp4', output.node.short_hash)


def test_stream_repr():
    in_file = ffmpeg.input('dummy.mp4')
    assert repr(in_file) == "input(filename={!r})[None] <{}>".format('dummy.mp4', in_file.node.short_hash)
    split0 = in_file.filter_multi_output('split')[0]
    assert repr(split0) == "split()[0] <{}>".format(split0.node.short_hash)
    dummy_out = in_file.filter_multi_output('dummy')['out']
    assert repr(dummy_out) == "dummy()[{!r}] <{}>".format(dummy_out.label, dummy_out.node.short_hash)


def test_get_args_simple():
    out_file = ffmpeg.input('dummy.mp4').output('dummy2.mp4')
    assert out_file.get_args() == ['-i', 'dummy.mp4', 'dummy2.mp4']


def _get_complex_filter_example():
    split = (ffmpeg
        .input(TEST_INPUT_FILE)
        .vflip()
        .split()
    )
    split0 = split[0]
    split1 = split[1]

    overlay_file = ffmpeg.input(TEST_OVERLAY_FILE)
    return (ffmpeg
        .concat(
            split0.trim(start_frame=10, end_frame=20),
            split1.trim(start_frame=30, end_frame=40),
        )
        .overlay(overlay_file.hflip())
        .drawbox(50, 50, 120, 120, color='red', thickness=5)
        .output(TEST_OUTPUT_FILE)
        .overwrite_output()
    )


def test_get_args_complex_filter():
    out = _get_complex_filter_example()
    args = ffmpeg.get_args(out)
    assert args == ['-i', TEST_INPUT_FILE,
        '-i', TEST_OVERLAY_FILE,
        '-filter_complex',
            '[0]vflip[s0];' \
            '[s0]split[s1][s2];' \
            '[s1]trim=end_frame=20:start_frame=10[s3];' \
            '[s2]trim=end_frame=40:start_frame=30[s4];' \
            '[s3][s4]concat=n=2[s5];' \
            '[1]hflip[s6];' \
            '[s5][s6]overlay=eof_action=repeat[s7];' \
            '[s7]drawbox=50:50:120:120:red:t=5[s8]',
        '-map', '[s8]', os.path.join(SAMPLE_DATA_DIR, 'dummy2.mp4'),
        '-y'
    ]



#def test_version():
#    subprocess.check_call(['ffmpeg', '-version'])


def test_run():
    node = _get_complex_filter_example()
    ffmpeg.run(node)


def test_run_dummy_cmd():
    node = _get_complex_filter_example()
    ffmpeg.run(node, cmd='true')


def test_run_dummy_cmd_list():
    node = _get_complex_filter_example()
    ffmpeg.run(node, cmd=['true', 'ignored'])


def test_run_failing_cmd():
    node = _get_complex_filter_example()
    with pytest.raises(subprocess.CalledProcessError):
        ffmpeg.run(node, cmd='false')


def test_custom_filter():
    node = ffmpeg.input('dummy.mp4')
    node = ffmpeg.filter_(node, 'custom_filter', 'a', 'b', kwarg1='c')
    node = ffmpeg.output(node, 'dummy2.mp4')
    assert node.get_args() == [
        '-i', 'dummy.mp4',
        '-filter_complex', '[0]custom_filter=a:b:kwarg1=c[s0]',
        '-map', '[s0]',
        'dummy2.mp4'
    ]


def test_custom_filter_fluent():
    node = (ffmpeg
        .input('dummy.mp4')
        .filter_('custom_filter', 'a', 'b', kwarg1='c')
        .output('dummy2.mp4')
    )
    assert node.get_args() == [
        '-i', 'dummy.mp4',
        '-filter_complex', '[0]custom_filter=a:b:kwarg1=c[s0]',
        '-map', '[s0]',
        'dummy2.mp4'
    ]


def test_pipe():
    width = 32
    height = 32
    frame_size = width * height * 3  # 3 bytes for rgb24
    frame_count = 10
    start_frame = 2

    out = (ffmpeg
        .input('pipe:0', format='rawvideo', pixel_format='rgb24', video_size=(width, height), framerate=10)
        .trim(start_frame=start_frame)
        .output('pipe:1', format='rawvideo')
    )

    args = out.get_args()
    assert args == [
        '-f', 'rawvideo',
        '-video_size', '{}x{}'.format(width, height),
        '-framerate', '10',
        '-pixel_format', 'rgb24',
        '-i', 'pipe:0',
        '-filter_complex',
            '[0]trim=start_frame=2[s0]',
        '-map', '[s0]',
        '-f', 'rawvideo',
        'pipe:1'
    ]

    cmd = ['ffmpeg'] + args
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    in_data = bytes(bytearray([random.randint(0,255) for _ in range(frame_size * frame_count)]))
    p.stdin.write(in_data)  # note: this could block, in which case need to use threads
    p.stdin.close()

    out_data = p.stdout.read()
    assert len(out_data) == frame_size * (frame_count - start_frame)
    assert out_data == in_data[start_frame*frame_size:]
