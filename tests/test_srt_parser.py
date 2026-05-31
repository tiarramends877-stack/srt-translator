"""测试 SRT 解析与序列化。"""

import textwrap

import pytest

from srt_translator.srt_parser import parse_srt, serialize_srt


SAMPLE_SRT = textwrap.dedent("""\
    1
    00:00:01,500 --> 00:00:05,000
    Hello everyone, and welcome to today's episode.

    2
    00:00:05,500 --> 00:00:09,000
    We're going to explore the future of artificial intelligence.

    3
    00:00:10,000 --> 00:00:14,500
    First, let's talk about how machines learn from data.

    4
    00:00:15,000 --> 00:00:19,000
    It's a lot like teaching a child
    to recognize different animals.

    5
    00:00:20,000 --> 00:00:24,500
    Stay tuned — you won't want to miss this.
    """)


def test_parse_count():
    """解析应返回正确数量的字幕条目。"""
    blocks = parse_srt(SAMPLE_SRT)
    assert len(blocks) == 5


def test_parse_index():
    """编号应正确保留。"""
    blocks = parse_srt(SAMPLE_SRT)
    assert blocks[0]["index"] == 1
    assert blocks[4]["index"] == 5


def test_parse_timestamps():
    """时间轴应正确解析。"""
    blocks = parse_srt(SAMPLE_SRT)
    assert blocks[0]["start"] == "00:00:01.500"
    assert blocks[0]["end"] == "00:00:05.000"
    assert blocks[4]["start"] == "00:00:20.000"
    assert blocks[4]["end"] == "00:00:24.500"


def test_parse_multiline_text():
    """多行字幕文本应保留换行。"""
    blocks = parse_srt(SAMPLE_SRT)
    assert "\n" in blocks[3]["text"]
    assert "teaching a child" in blocks[3]["text"]
    assert "recognize different animals" in blocks[3]["text"]


def test_parse_empty():
    """空文本应返回空列表。"""
    blocks = parse_srt("")
    assert blocks == []


def test_round_trip():
    """parse → serialize → parse 应保持一致。"""
    blocks = parse_srt(SAMPLE_SRT)
    serialized = serialize_srt(blocks)
    blocks2 = parse_srt(serialized)

    assert len(blocks2) == len(blocks)
    for b1, b2 in zip(blocks, blocks2):
        assert b1["start"] == b2["start"]
        assert b1["end"] == b2["end"]
        assert b1["text"] == b2["text"]


def test_serialize_numbering():
    """序列化时编号应从 1 开始递増。"""
    blocks = [
        {"index": 5, "start": "00:00:01.000", "end": "00:00:02.000", "text": "Hello"},
        {"index": 99, "start": "00:00:03.000", "end": "00:00:04.000", "text": "World"},
    ]
    output = serialize_srt(blocks)
    lines = output.strip().split("\n")
    assert lines[0] == "1"
    # 第二个 block 的编号应该在空行之后
    assert "2" in [l for l in lines if l == "2"]


def test_serialize_timestamps_use_comma():
    """序列化时间轴应使用逗号分隔毫秒（SRT 标准格式）。"""
    blocks = [
        {"index": 1, "start": "00:00:01.500", "end": "00:00:05.000", "text": "Hi"},
    ]
    output = serialize_srt(blocks)
    assert "00:00:01,500 --> 00:00:05,000" in output


def test_parse_dot_timestamps():
    """解析时应兼容小数点格式的时间轴。"""
    srt = "1\n00:00:01.500 --> 00:00:05.000\nHello.\n"
    blocks = parse_srt(srt)
    assert len(blocks) == 1
    assert blocks[0]["start"] == "00:00:01.500"
