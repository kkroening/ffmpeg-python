from __future__ import unicode_literals

from builtins import bytes
from builtins import range
import ffmpeg
import os
import pytest
import random
import re
import subprocess


TEST_DIR = os.path.dirname(__file__)
SAMPLE_DATA_DIR = os.path.join(TEST_DIR, 'sample_data')
TEST_INPUT_FILE1 = os.path.join(SAMPLE_DATA_DIR, 'in1.mp4')
TEST_OVERLAY_FILE = os.path.join(SAMPLE_DATA_DIR, 'overlay.png')
TEST_OUTPUT_FILE1 = os.path.join(SAMPLE_DATA_DIR, 'out1.mp4')
TEST_OUTPUT_FILE2 = os.path.join(SAMPLE_DATA_DIR, 'out2.mp4')


subprocess.check_call(['ffmpeg', '-version'])


def test_escape_chars():
    assert ffmpeg._utils.escape_chars('a:b', ':') == 'a\:b'
    assert ffmpeg._utils.escape_chars('a\\:b', ':\\') == 'a\\\\\\:b'
    assert ffmpeg._utils.escape_chars('a:b,c[d]e%{}f\'g\'h\\i', '\\\':,[]%') == 'a\\:b\\,c\\[d\\]e\\%{}f\\\'g\\\'h\\\\i'
    assert ffmpeg._utils.escape_chars(123, ':\\') == '123'


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
        .input(TEST_INPUT_FILE1)
        .vflip()
        .split()
    )
    split0 = split[0]
    split1 = split[1]

    overlay_file = ffmpeg.input(TEST_OVERLAY_FILE)
    overlay_file = ffmpeg.crop(overlay_file, 10, 10, 158, 112)
    return (ffmpeg
        .concat(
            split0.trim(start_frame=10, end_frame=20),
            split1.trim(start_frame=30, end_frame=40),
        )
        .overlay(overlay_file.hflip())
        .drawbox(50, 50, 120, 120, color='red', thickness=5)
        .output(TEST_OUTPUT_FILE1)
        .overwrite_output()
    )


def test_get_args_complex_filter():
    out = _get_complex_filter_example()
    args = ffmpeg.get_args(out)
    assert args == ['-i', TEST_INPUT_FILE1,
        '-i', TEST_OVERLAY_FILE,
        '-filter_complex',
            '[0]vflip[s0];' \
            '[s0]split=2[s1][s2];' \
            '[s1]trim=end_frame=20:start_frame=10[s3];' \
            '[s2]trim=end_frame=40:start_frame=30[s4];' \
            '[s3][s4]concat=n=2[s5];' \
            '[1]crop=158:112:10:10[s6];' \
            '[s6]hflip[s7];' \
            '[s5][s7]overlay=eof_action=repeat[s8];' \
            '[s8]drawbox=50:50:120:120:red:t=5[s9]',
        '-map', '[s9]', TEST_OUTPUT_FILE1,
        '-y'
    ]


def test_filter_normal_arg_escape():
    """Test string escaping of normal filter args (e.g. ``font`` param of ``drawtext`` filter)."""
    def _get_drawtext_font_repr(font):
        """Build a command-line arg using drawtext ``font`` param and extract the ``-filter_complex`` arg."""
        args = (ffmpeg
            .input('in')
            .drawtext('test', font='a{}b'.format(font))
            .output('out')
            .get_args()
        )
        assert args[:3] == ['-i', 'in', '-filter_complex']
        assert args[4:] == ['-map', '[s0]', 'out']
        match = re.match(r'\[0\]drawtext=font=a((.|\n)*)b:text=test\[s0\]', args[3], re.MULTILINE)
        assert match is not None, 'Invalid -filter_complex arg: {!r}'.format(args[3])
        return match.group(1)

    expected_backslash_counts = {
        'x': 0,
        '\'': 3,
        '\\': 3,
        '%': 0,
        ':': 2,
        ',': 1,
        '[': 1,
        ']': 1,
        '=': 2,
        '\n': 0,
    }
    for ch, expected_backslash_count in list(expected_backslash_counts.items()):
        expected = '{}{}'.format('\\' * expected_backslash_count, ch)
        actual = _get_drawtext_font_repr(ch)
        assert expected == actual


def test_filter_text_arg_str_escape():
    """Test string escaping of normal filter args (e.g. ``text`` param of ``drawtext`` filter)."""
    def _get_drawtext_text_repr(text):
        """Build a command-line arg using drawtext ``text`` param and extract the ``-filter_complex`` arg."""
        args = (ffmpeg
            .input('in')
            .drawtext('a{}b'.format(text))
            .output('out')
            .get_args()
        )
        assert args[:3] == ['-i', 'in', '-filter_complex']
        assert args[4:] == ['-map', '[s0]', 'out']
        match = re.match(r'\[0\]drawtext=text=a((.|\n)*)b\[s0\]', args[3], re.MULTILINE)
        assert match is not None, 'Invalid -filter_complex arg: {!r}'.format(args[3])
        return match.group(1)

    expected_backslash_counts = {
        'x': 0,
        '\'': 7,
        '\\': 7,
        '%': 4,
        ':': 2,
        ',': 1,
        '[': 1,
        ']': 1,
        '=': 2,
        '\n': 0,
    }
    for ch, expected_backslash_count in list(expected_backslash_counts.items()):
        expected = '{}{}'.format('\\' * expected_backslash_count, ch)
        actual = _get_drawtext_text_repr(ch)
        assert expected == actual


#def test_version():
#    subprocess.check_call(['ffmpeg', '-version'])


def test_compile():
    out_file = ffmpeg.input('dummy.mp4').output('dummy2.mp4')
    assert out_file.compile() == ['ffmpeg', '-i', 'dummy.mp4', 'dummy2.mp4']
    assert out_file.compile(cmd='ffmpeg.old') == ['ffmpeg.old', '-i', 'dummy.mp4', 'dummy2.mp4']


def test_run():
    stream = _get_complex_filter_example()
    ffmpeg.run(stream)


def test_run_multi_output():
    in_ = ffmpeg.input(TEST_INPUT_FILE1)
    out1 = in_.output(TEST_OUTPUT_FILE1)
    out2 = in_.output(TEST_OUTPUT_FILE2)
    ffmpeg.run([out1, out2], overwrite_output=True)


def test_run_dummy_cmd():
    stream = _get_complex_filter_example()
    ffmpeg.run(stream, cmd='true')


def test_run_dummy_cmd_list():
    stream = _get_complex_filter_example()
    ffmpeg.run(stream, cmd=['true', 'ignored'])


def test_run_failing_cmd():
    stream = _get_complex_filter_example()
    with pytest.raises(subprocess.CalledProcessError):
        ffmpeg.run(stream, cmd='false')


def test_custom_filter():
    stream = ffmpeg.input('dummy.mp4')
    stream = ffmpeg.filter_(stream, 'custom_filter', 'a', 'b', kwarg1='c')
    stream = ffmpeg.output(stream, 'dummy2.mp4')
    assert stream.get_args() == [
        '-i', 'dummy.mp4',
        '-filter_complex', '[0]custom_filter=a:b:kwarg1=c[s0]',
        '-map', '[s0]',
        'dummy2.mp4'
    ]


def test_custom_filter_fluent():
    stream = (ffmpeg
        .input('dummy.mp4')
        .filter_('custom_filter', 'a', 'b', kwarg1='c')
        .output('dummy2.mp4')
    )
    assert stream.get_args() == [
        '-i', 'dummy.mp4',
        '-filter_complex', '[0]custom_filter=a:b:kwarg1=c[s0]',
        '-map', '[s0]',
        'dummy2.mp4'
    ]


def test_merge_outputs():
    in_ = ffmpeg.input('in.mp4')
    out1 = in_.output('out1.mp4')
    out2 = in_.output('out2.mp4')
    assert ffmpeg.merge_outputs(out1, out2).get_args() == [
        '-i', 'in.mp4', 'out1.mp4', 'out2.mp4'
    ]
    assert ffmpeg.get_args([out1, out2]) == [
        '-i', 'in.mp4', 'out2.mp4', 'out1.mp4'
    ]


def test__input__start_time():
    assert ffmpeg.input('in', ss=10.5).output('out').get_args() == ['-ss', '10.5', '-i', 'in', 'out']
    assert ffmpeg.input('in', ss=0.0).output('out').get_args() == ['-ss', '0.0', '-i', 'in', 'out']


def test_multi_passthrough():
    out1 = ffmpeg.input('in1.mp4').output('out1.mp4')
    out2 = ffmpeg.input('in2.mp4').output('out2.mp4')
    out = ffmpeg.merge_outputs(out1, out2)
    assert ffmpeg.get_args(out) == [
        '-i', 'in1.mp4',
        '-i', 'in2.mp4',
        'out1.mp4',
        '-map', '[1]',  # FIXME: this should not be here (see #23)
        'out2.mp4'
    ]
    assert ffmpeg.get_args([out1, out2]) == [
        '-i', 'in2.mp4',
        '-i', 'in1.mp4',
        'out2.mp4',
        '-map', '[1]',  # FIXME: this should not be here (see #23)
        'out1.mp4'
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
