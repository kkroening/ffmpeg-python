from __future__ import unicode_literals
from builtins import bytes
from builtins import range
from builtins import str
import ffmpeg
import os
import pytest
import random
import re
import subprocess
import sys


try:
    import mock  # python 2
except ImportError:
    from unittest import mock  # python 3


TEST_DIR = os.path.dirname(__file__)
SAMPLE_DATA_DIR = os.path.join(TEST_DIR, 'sample_data')
TEST_INPUT_FILE1 = os.path.join(SAMPLE_DATA_DIR, 'in1.mp4')
TEST_OVERLAY_FILE = os.path.join(SAMPLE_DATA_DIR, 'overlay.png')
TEST_OUTPUT_FILE1 = os.path.join(SAMPLE_DATA_DIR, 'out1.mp4')
TEST_OUTPUT_FILE2 = os.path.join(SAMPLE_DATA_DIR, 'out2.mp4')
BOGUS_INPUT_FILE = os.path.join(SAMPLE_DATA_DIR, 'bogus')


subprocess.check_call(['ffmpeg', '-version'])


def test_escape_chars():
    assert ffmpeg._utils.escape_chars('a:b', ':') == 'a\:b'
    assert ffmpeg._utils.escape_chars('a\\:b', ':\\') == 'a\\\\\\:b'
    assert (
        ffmpeg._utils.escape_chars('a:b,c[d]e%{}f\'g\'h\\i', '\\\':,[]%')
        == 'a\\:b\\,c\\[d\\]e\\%{}f\\\'g\\\'h\\\\i'
    )
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
    ffmpeg.input('dummy.mp4').trim(start_frame=10, end_frame=20).output('dummy2.mp4')


def test_fluent_complex_filter():
    in_file = ffmpeg.input('dummy.mp4')
    return ffmpeg.concat(
        in_file.trim(start_frame=10, end_frame=20),
        in_file.trim(start_frame=30, end_frame=40),
        in_file.trim(start_frame=50, end_frame=60),
    ).output('dummy2.mp4')


def test_node_repr():
    in_file = ffmpeg.input('dummy.mp4')
    trim1 = ffmpeg.trim(in_file, start_frame=10, end_frame=20)
    trim2 = ffmpeg.trim(in_file, start_frame=30, end_frame=40)
    trim3 = ffmpeg.trim(in_file, start_frame=50, end_frame=60)
    concatted = ffmpeg.concat(trim1, trim2, trim3)
    output = ffmpeg.output(concatted, 'dummy2.mp4')
    assert repr(in_file.node) == 'input(filename={!r}) <{}>'.format(
        'dummy.mp4', in_file.node.short_hash
    )
    assert repr(trim1.node) == 'trim(end_frame=20, start_frame=10) <{}>'.format(
        trim1.node.short_hash
    )
    assert repr(trim2.node) == 'trim(end_frame=40, start_frame=30) <{}>'.format(
        trim2.node.short_hash
    )
    assert repr(trim3.node) == 'trim(end_frame=60, start_frame=50) <{}>'.format(
        trim3.node.short_hash
    )
    assert repr(concatted.node) == 'concat(n=3) <{}>'.format(concatted.node.short_hash)
    assert repr(output.node) == 'output(filename={!r}) <{}>'.format(
        'dummy2.mp4', output.node.short_hash
    )


def test_stream_repr():
    in_file = ffmpeg.input('dummy.mp4')
    assert repr(in_file) == 'input(filename={!r})[None] <{}>'.format(
        'dummy.mp4', in_file.node.short_hash
    )
    split0 = in_file.filter_multi_output('split')[0]
    assert repr(split0) == 'split()[0] <{}>'.format(split0.node.short_hash)
    dummy_out = in_file.filter_multi_output('dummy')['out']
    assert repr(dummy_out) == 'dummy()[{!r}] <{}>'.format(
        dummy_out.label, dummy_out.node.short_hash
    )

def test_repeated_args():
    out_file = ffmpeg.input('dummy.mp4').output('dummy2.mp4', streamid=['0:0x101', '1:0x102'])
    assert out_file.get_args() == ['-i', 'dummy.mp4', '-streamid', '0:0x101', '-streamid', '1:0x102', 'dummy2.mp4']


def test__get_args__simple():
    out_file = ffmpeg.input('dummy.mp4').output('dummy2.mp4')
    assert out_file.get_args() == ['-i', 'dummy.mp4', 'dummy2.mp4']


def test_global_args():
    out_file = (
        ffmpeg.input('dummy.mp4')
        .output('dummy2.mp4')
        .global_args('-progress', 'someurl')
    )
    assert out_file.get_args() == [
        '-i',
        'dummy.mp4',
        'dummy2.mp4',
        '-progress',
        'someurl',
    ]


def _get_simple_example():
    return ffmpeg.input(TEST_INPUT_FILE1).output(TEST_OUTPUT_FILE1)


def _get_complex_filter_example():
    split = ffmpeg.input(TEST_INPUT_FILE1).vflip().split()
    split0 = split[0]
    split1 = split[1]

    overlay_file = ffmpeg.input(TEST_OVERLAY_FILE)
    overlay_file = ffmpeg.crop(overlay_file, 10, 10, 158, 112)
    return (
        ffmpeg.concat(
            split0.trim(start_frame=10, end_frame=20),
            split1.trim(start_frame=30, end_frame=40),
        )
        .overlay(overlay_file.hflip())
        .drawbox(50, 50, 120, 120, color='red', thickness=5)
        .output(TEST_OUTPUT_FILE1)
        .overwrite_output()
    )


def test__get_args__complex_filter():
    out = _get_complex_filter_example()
    args = ffmpeg.get_args(out)
    assert args == [
        '-i',
        TEST_INPUT_FILE1,
        '-i',
        TEST_OVERLAY_FILE,
        '-filter_complex',
        '[0]vflip[s0];'
        '[s0]split=2[s1][s2];'
        '[s1]trim=end_frame=20:start_frame=10[s3];'
        '[s2]trim=end_frame=40:start_frame=30[s4];'
        '[s3][s4]concat=n=2[s5];'
        '[1]crop=158:112:10:10[s6];'
        '[s6]hflip[s7];'
        '[s5][s7]overlay=eof_action=repeat[s8];'
        '[s8]drawbox=50:50:120:120:red:t=5[s9]',
        '-map',
        '[s9]',
        TEST_OUTPUT_FILE1,
        '-y',
    ]


def test_combined_output():
    i1 = ffmpeg.input(TEST_INPUT_FILE1)
    i2 = ffmpeg.input(TEST_OVERLAY_FILE)
    out = ffmpeg.output(i1, i2, TEST_OUTPUT_FILE1)
    assert out.get_args() == [
        '-i',
        TEST_INPUT_FILE1,
        '-i',
        TEST_OVERLAY_FILE,
        '-map',
        '0',
        '-map',
        '1',
        TEST_OUTPUT_FILE1,
    ]


@pytest.mark.parametrize('use_shorthand', [True, False])
def test_filter_with_selector(use_shorthand):
    i = ffmpeg.input(TEST_INPUT_FILE1)
    if use_shorthand:
        v1 = i.video.hflip()
        a1 = i.audio.filter('aecho', 0.8, 0.9, 1000, 0.3)
    else:
        v1 = i['v'].hflip()
        a1 = i['a'].filter('aecho', 0.8, 0.9, 1000, 0.3)
    out = ffmpeg.output(a1, v1, TEST_OUTPUT_FILE1)
    assert out.get_args() == [
        '-i',
        TEST_INPUT_FILE1,
        '-filter_complex',
        '[0:a]aecho=0.8:0.9:1000:0.3[s0];' '[0:v]hflip[s1]',
        '-map',
        '[s0]',
        '-map',
        '[s1]',
        TEST_OUTPUT_FILE1,
    ]


def test_get_item_with_bad_selectors():
    input = ffmpeg.input(TEST_INPUT_FILE1)

    with pytest.raises(ValueError) as excinfo:
        input['a']['a']
    assert str(excinfo.value).startswith('Stream already has a selector:')

    with pytest.raises(TypeError) as excinfo:
        input[:'a']
    assert str(excinfo.value).startswith("Expected string index (e.g. 'a')")

    with pytest.raises(TypeError) as excinfo:
        input[5]
    assert str(excinfo.value).startswith("Expected string index (e.g. 'a')")


def _get_complex_filter_asplit_example():
    split = ffmpeg.input(TEST_INPUT_FILE1).vflip().asplit()
    split0 = split[0]
    split1 = split[1]

    return (
        ffmpeg.concat(
            split0.filter('atrim', start=10, end=20),
            split1.filter('atrim', start=30, end=40),
        )
        .output(TEST_OUTPUT_FILE1)
        .overwrite_output()
    )


def test_filter_concat__video_only():
    in1 = ffmpeg.input('in1.mp4')
    in2 = ffmpeg.input('in2.mp4')
    args = ffmpeg.concat(in1, in2).output('out.mp4').get_args()
    assert args == [
        '-i',
        'in1.mp4',
        '-i',
        'in2.mp4',
        '-filter_complex',
        '[0][1]concat=n=2[s0]',
        '-map',
        '[s0]',
        'out.mp4',
    ]


def test_filter_concat__audio_only():
    in1 = ffmpeg.input('in1.mp4')
    in2 = ffmpeg.input('in2.mp4')
    args = ffmpeg.concat(in1, in2, v=0, a=1).output('out.mp4').get_args()
    assert args == [
        '-i',
        'in1.mp4',
        '-i',
        'in2.mp4',
        '-filter_complex',
        '[0][1]concat=a=1:n=2:v=0[s0]',
        '-map',
        '[s0]',
        'out.mp4',
    ]


def test_filter_concat__audio_video():
    in1 = ffmpeg.input('in1.mp4')
    in2 = ffmpeg.input('in2.mp4')
    joined = ffmpeg.concat(in1.video, in1.audio, in2.hflip(), in2['a'], v=1, a=1).node
    args = ffmpeg.output(joined[0], joined[1], 'out.mp4').get_args()
    assert args == [
        '-i',
        'in1.mp4',
        '-i',
        'in2.mp4',
        '-filter_complex',
        '[1]hflip[s0];[0:v][0:a][s0][1:a]concat=a=1:n=2:v=1[s1][s2]',
        '-map',
        '[s1]',
        '-map',
        '[s2]',
        'out.mp4',
    ]


def test_filter_concat__wrong_stream_count():
    in1 = ffmpeg.input('in1.mp4')
    in2 = ffmpeg.input('in2.mp4')
    with pytest.raises(ValueError) as excinfo:
        ffmpeg.concat(in1.video, in1.audio, in2.hflip(), v=1, a=1).node
    assert (
        str(excinfo.value)
        == 'Expected concat input streams to have length multiple of 2 (v=1, a=1); got 3'
    )


def test_filter_asplit():
    out = _get_complex_filter_asplit_example()
    args = out.get_args()
    assert args == [
        '-i',
        TEST_INPUT_FILE1,
        '-filter_complex',
        '[0]vflip[s0];[s0]asplit=2[s1][s2];[s1]atrim=end=20:start=10[s3];[s2]atrim=end=40:start=30[s4];[s3]'
        '[s4]concat=n=2[s5]',
        '-map',
        '[s5]',
        TEST_OUTPUT_FILE1,
        '-y',
    ]


def test__output__bitrate():
    args = (
        ffmpeg.input('in')
        .output('out', video_bitrate=1000, audio_bitrate=200)
        .get_args()
    )
    assert args == ['-i', 'in', '-b:v', '1000', '-b:a', '200', 'out']


@pytest.mark.parametrize('video_size', [(320, 240), '320x240'])
def test__output__video_size(video_size):
    args = ffmpeg.input('in').output('out', video_size=video_size).get_args()
    assert args == ['-i', 'in', '-video_size', '320x240', 'out']


def test_filter_normal_arg_escape():
    """Test string escaping of normal filter args (e.g. ``font`` param of ``drawtext`` filter)."""

    def _get_drawtext_font_repr(font):
        """Build a command-line arg using drawtext ``font`` param and extract the ``-filter_complex`` arg."""
        args = (
            ffmpeg.input('in')
            .drawtext('test', font='a{}b'.format(font))
            .output('out')
            .get_args()
        )
        assert args[:3] == ['-i', 'in', '-filter_complex']
        assert args[4:] == ['-map', '[s0]', 'out']
        match = re.match(
            r'\[0\]drawtext=font=a((.|\n)*)b:text=test\[s0\]', args[3], re.MULTILINE
        )
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
        args = ffmpeg.input('in').drawtext('a{}b'.format(text)).output('out').get_args()
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


# def test_version():
#    subprocess.check_call(['ffmpeg', '-version'])


def test__compile():
    out_file = ffmpeg.input('dummy.mp4').output('dummy2.mp4')
    assert out_file.compile() == ['ffmpeg', '-i', 'dummy.mp4', 'dummy2.mp4']
    assert out_file.compile(cmd='ffmpeg.old') == [
        'ffmpeg.old',
        '-i',
        'dummy.mp4',
        'dummy2.mp4',
    ]


@pytest.mark.parametrize('pipe_stdin', [True, False])
@pytest.mark.parametrize('pipe_stdout', [True, False])
@pytest.mark.parametrize('pipe_stderr', [True, False])
@pytest.mark.parametrize('cwd', [None, '/tmp'])
def test__run_async(mocker, pipe_stdin, pipe_stdout, pipe_stderr, cwd):
    process__mock = mock.Mock()
    popen__mock = mocker.patch.object(subprocess, 'Popen', return_value=process__mock)
    stream = _get_simple_example()
    process = ffmpeg.run_async(
        stream, pipe_stdin=pipe_stdin, pipe_stdout=pipe_stdout,
        pipe_stderr=pipe_stderr, cwd=cwd
    )
    assert process is process__mock

    expected_stdin = subprocess.PIPE if pipe_stdin else None
    expected_stdout = subprocess.PIPE if pipe_stdout else None
    expected_stderr = subprocess.PIPE if pipe_stderr else None
    (args,), kwargs = popen__mock.call_args
    assert args == ffmpeg.compile(stream)
    assert kwargs == dict(
        stdin=expected_stdin, stdout=expected_stdout, stderr=expected_stderr,
        cwd=cwd
    )


def test__run():
    stream = _get_complex_filter_example()
    out, err = ffmpeg.run(stream)
    assert out is None
    assert err is None


@pytest.mark.parametrize('capture_stdout', [True, False])
@pytest.mark.parametrize('capture_stderr', [True, False])
def test__run__capture_out(mocker, capture_stdout, capture_stderr):
    mocker.patch.object(ffmpeg._run, 'compile', return_value=['echo', 'test'])
    stream = _get_simple_example()
    out, err = ffmpeg.run(
        stream, capture_stdout=capture_stdout, capture_stderr=capture_stderr
    )
    if capture_stdout:
        assert out == 'test\n'.encode()
    else:
        assert out is None
    if capture_stderr:
        assert err == ''.encode()
    else:
        assert err is None


def test__run__input_output(mocker):
    mocker.patch.object(ffmpeg._run, 'compile', return_value=['cat'])
    stream = _get_simple_example()
    out, err = ffmpeg.run(stream, input='test'.encode(), capture_stdout=True)
    assert out == 'test'.encode()
    assert err is None


@pytest.mark.parametrize('capture_stdout', [True, False])
@pytest.mark.parametrize('capture_stderr', [True, False])
def test__run__error(mocker, capture_stdout, capture_stderr):
    mocker.patch.object(ffmpeg._run, 'compile', return_value=['ffmpeg'])
    stream = _get_complex_filter_example()
    with pytest.raises(ffmpeg.Error) as excinfo:
        out, err = ffmpeg.run(
            stream, capture_stdout=capture_stdout, capture_stderr=capture_stderr
        )
    assert str(excinfo.value) == 'ffmpeg error (see stderr output for detail)'
    out = excinfo.value.stdout
    err = excinfo.value.stderr
    if capture_stdout:
        assert out == ''.encode()
    else:
        assert out is None
    if capture_stderr:
        assert err.decode().startswith('ffmpeg version')
    else:
        assert err is None


def test__run__multi_output():
    in_ = ffmpeg.input(TEST_INPUT_FILE1)
    out1 = in_.output(TEST_OUTPUT_FILE1)
    out2 = in_.output(TEST_OUTPUT_FILE2)
    ffmpeg.run([out1, out2], overwrite_output=True)


def test__run__dummy_cmd():
    stream = _get_complex_filter_example()
    ffmpeg.run(stream, cmd='true')


def test__run__dummy_cmd_list():
    stream = _get_complex_filter_example()
    ffmpeg.run(stream, cmd=['true', 'ignored'])


def test__filter__custom():
    stream = ffmpeg.input('dummy.mp4')
    stream = ffmpeg.filter(stream, 'custom_filter', 'a', 'b', kwarg1='c')
    stream = ffmpeg.output(stream, 'dummy2.mp4')
    assert stream.get_args() == [
        '-i',
        'dummy.mp4',
        '-filter_complex',
        '[0]custom_filter=a:b:kwarg1=c[s0]',
        '-map',
        '[s0]',
        'dummy2.mp4',
    ]


def test__filter__custom_fluent():
    stream = (
        ffmpeg.input('dummy.mp4')
        .filter('custom_filter', 'a', 'b', kwarg1='c')
        .output('dummy2.mp4')
    )
    assert stream.get_args() == [
        '-i',
        'dummy.mp4',
        '-filter_complex',
        '[0]custom_filter=a:b:kwarg1=c[s0]',
        '-map',
        '[s0]',
        'dummy2.mp4',
    ]


def test__merge_outputs():
    in_ = ffmpeg.input('in.mp4')
    out1 = in_.output('out1.mp4')
    out2 = in_.output('out2.mp4')
    assert ffmpeg.merge_outputs(out1, out2).get_args() == [
        '-i',
        'in.mp4',
        'out1.mp4',
        'out2.mp4',
    ]
    assert ffmpeg.get_args([out1, out2]) == ['-i', 'in.mp4', 'out2.mp4', 'out1.mp4']


def test__input__start_time():
    assert ffmpeg.input('in', ss=10.5).output('out').get_args() == [
        '-ss',
        '10.5',
        '-i',
        'in',
        'out',
    ]
    assert ffmpeg.input('in', ss=0.0).output('out').get_args() == [
        '-ss',
        '0.0',
        '-i',
        'in',
        'out',
    ]


def test_multi_passthrough():
    out1 = ffmpeg.input('in1.mp4').output('out1.mp4')
    out2 = ffmpeg.input('in2.mp4').output('out2.mp4')
    out = ffmpeg.merge_outputs(out1, out2)
    assert ffmpeg.get_args(out) == [
        '-i',
        'in1.mp4',
        '-i',
        'in2.mp4',
        'out1.mp4',
        '-map',
        '1',
        'out2.mp4',
    ]
    assert ffmpeg.get_args([out1, out2]) == [
        '-i',
        'in2.mp4',
        '-i',
        'in1.mp4',
        'out2.mp4',
        '-map',
        '1',
        'out1.mp4',
    ]


def test_passthrough_selectors():
    i1 = ffmpeg.input(TEST_INPUT_FILE1)
    args = ffmpeg.output(i1['1'], i1['2'], TEST_OUTPUT_FILE1).get_args()
    assert args == [
        '-i',
        TEST_INPUT_FILE1,
        '-map',
        '0:1',
        '-map',
        '0:2',
        TEST_OUTPUT_FILE1,
    ]


def test_mixed_passthrough_selectors():
    i1 = ffmpeg.input(TEST_INPUT_FILE1)
    args = ffmpeg.output(i1['1'].hflip(), i1['2'], TEST_OUTPUT_FILE1).get_args()
    assert args == [
        '-i',
        TEST_INPUT_FILE1,
        '-filter_complex',
        '[0:1]hflip[s0]',
        '-map',
        '[s0]',
        '-map',
        '0:2',
        TEST_OUTPUT_FILE1,
    ]


def test_pipe():
    width = 32
    height = 32
    frame_size = width * height * 3  # 3 bytes for rgb24
    frame_count = 10
    start_frame = 2

    out = (
        ffmpeg.input(
            'pipe:0',
            format='rawvideo',
            pixel_format='rgb24',
            video_size=(width, height),
            framerate=10,
        )
        .trim(start_frame=start_frame)
        .output('pipe:1', format='rawvideo')
    )

    args = out.get_args()
    assert args == [
        '-f',
        'rawvideo',
        '-video_size',
        '{}x{}'.format(width, height),
        '-framerate',
        '10',
        '-pixel_format',
        'rgb24',
        '-i',
        'pipe:0',
        '-filter_complex',
        '[0]trim=start_frame=2[s0]',
        '-map',
        '[s0]',
        '-f',
        'rawvideo',
        'pipe:1',
    ]

    cmd = ['ffmpeg'] + args
    p = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    in_data = bytes(
        bytearray([random.randint(0, 255) for _ in range(frame_size * frame_count)])
    )
    p.stdin.write(in_data)  # note: this could block, in which case need to use threads
    p.stdin.close()

    out_data = p.stdout.read()
    assert len(out_data) == frame_size * (frame_count - start_frame)
    assert out_data == in_data[start_frame * frame_size :]


def test__probe():
    data = ffmpeg.probe(TEST_INPUT_FILE1)
    assert set(data.keys()) == {'format', 'streams'}
    assert data['format']['duration'] == '7.036000'


@pytest.mark.skipif(sys.version_info < (3, 3), reason="requires python3.3 or higher")
def test__probe_timeout():
    with pytest.raises(subprocess.TimeoutExpired) as excinfo:
        data = ffmpeg.probe(TEST_INPUT_FILE1, timeout=0)
    assert 'timed out after 0 seconds' in str(excinfo.value)


def test__probe__exception():
    with pytest.raises(ffmpeg.Error) as excinfo:
        ffmpeg.probe(BOGUS_INPUT_FILE)
    assert str(excinfo.value) == 'ffprobe error (see stderr output for detail)'
    assert 'No such file or directory'.encode() in excinfo.value.stderr


def test__probe__extra_args():
    data = ffmpeg.probe(TEST_INPUT_FILE1, show_frames=None)
    assert set(data.keys()) == {'format', 'streams', 'frames'}


def get_filter_complex_input(flt, name):
    m = re.search(r'\[([^]]+)\]{}(?=[[;]|$)'.format(name), flt)
    if m:
        return m.group(1)
    else:
        return None


def get_filter_complex_outputs(flt, name):
    m = re.search(r'(^|[];]){}((\[[^]]+\])+)(?=;|$)'.format(name), flt)
    if m:
        return m.group(2)[1:-1].split('][')
    else:
        return None


def test__get_filter_complex_input():
    assert get_filter_complex_input("", "scale") is None
    assert get_filter_complex_input("scale", "scale") is None
    assert get_filter_complex_input("scale[s3][s4];etc", "scale") is None
    assert get_filter_complex_input("[s2]scale", "scale") == "s2"
    assert get_filter_complex_input("[s2]scale;etc", "scale") == "s2"
    assert get_filter_complex_input("[s2]scale[s3][s4];etc", "scale") == "s2"


def test__get_filter_complex_outputs():
    assert get_filter_complex_outputs("", "scale") is None
    assert get_filter_complex_outputs("scale", "scale") is None
    assert get_filter_complex_outputs("scalex[s0][s1]", "scale") is None
    assert get_filter_complex_outputs("scale[s0][s1]", "scale") == ['s0', 's1']
    assert get_filter_complex_outputs("[s5]scale[s0][s1]", "scale") == ['s0', 's1']
    assert get_filter_complex_outputs("[s5]scale[s1][s0]", "scale") == ['s1', 's0']
    assert get_filter_complex_outputs("[s5]scale[s1]", "scale") == ['s1']
    assert get_filter_complex_outputs("[s5]scale[s1];x", "scale") == ['s1']
    assert get_filter_complex_outputs("y;[s5]scale[s1];x", "scale") == ['s1']


def test__multi_output_edge_label_order():
    scale2ref = ffmpeg.filter_multi_output(
        [ffmpeg.input('x'), ffmpeg.input('y')], 'scale2ref'
    )
    out = ffmpeg.merge_outputs(
        scale2ref[1].filter('scale').output('a'),
        scale2ref[10000].filter('hflip').output('b'),
    )

    args = out.get_args()
    flt_cmpl = args[args.index('-filter_complex') + 1]
    out1, out2 = get_filter_complex_outputs(flt_cmpl, 'scale2ref')
    assert out1 == get_filter_complex_input(flt_cmpl, 'scale')
    assert out2 == get_filter_complex_input(flt_cmpl, 'hflip')
