"""测试输出文件名生成逻辑。"""

from pathlib import Path

from srt_translator.config import get_output_path


def test_en_srt_strips_en():
    """example.en.srt → example.zh.srt"""
    result = get_output_path(Path("example.en.srt"))
    assert result == Path("example.zh.srt")


def test_plain_srt():
    """movie.srt → movie.zh.srt"""
    result = get_output_path(Path("movie.srt"))
    assert result == Path("movie.zh.srt")


def test_with_directory():
    """路径中的目录部分应保留。"""
    result = get_output_path(Path("/some/path/video.en.srt"))
    assert result == Path("/some/path/video.zh.srt")


def test_no_en_marker():
    """文件名不含 .en 时直接替换 .srt。"""
    result = get_output_path(Path("subtitles.srt"))
    assert result == Path("subtitles.zh.srt")


def test_output_arg_overrides():
    """--output 参数应覆盖自动生成的文件名。"""
    result = get_output_path(Path("example.en.srt"), output_arg="custom.zh.srt")
    assert result == Path("custom.zh.srt")
