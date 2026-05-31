"""测试 FastAPI /translate-srt 端点。"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# 确保项目根目录可导入
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from server.main import app  # noqa: E402

client = TestClient(app)

SAMPLE_SRT = (
    "1\n"
    "00:00:01,500 --> 00:00:05,000\n"
    "Hello everyone, and welcome to today's episode.\n"
    "\n"
    "2\n"
    "00:00:05,500 --> 00:00:09,000\n"
    "We're going to explore the future of artificial intelligence.\n"
)


def _fake_translated_blocks(*args, **kwargs):
    """模拟 translate_blocks 返回中文 block。"""
    blocks = kwargs.get("blocks") or args[1]
    result = []
    for b in blocks:
        result.append({
            "index": b["index"],
            "start": b["start"],
            "end": b["end"],
            "text": f"[ZH] {b['text']}",
        })
    return result


@patch("server.main.translate_blocks", side_effect=_fake_translated_blocks)
def test_translate_srt_basic(_mock):
    """基础请求应返回正确的 output_filename 和 translated_content。"""
    resp = client.post("/translate-srt", json={
        "filename": "example.en.srt",
        "content": SAMPLE_SRT,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["output_filename"] == "example.zh.srt"
    assert "[ZH]" in data["translated_content"]
    assert "00:00:01,500 --> 00:00:05,000" in data["translated_content"]


@patch("server.main.translate_blocks", side_effect=_fake_translated_blocks)
def test_translate_srt_movie_filename(_mock):
    """movie.srt → movie.zh.srt。"""
    resp = client.post("/translate-srt", json={
        "filename": "movie.srt",
        "content": SAMPLE_SRT,
    })
    assert resp.status_code == 200
    assert resp.json()["output_filename"] == "movie.zh.srt"


@patch("server.main.translate_blocks", side_effect=_fake_translated_blocks)
def test_translate_srt_preserves_timestamps(_mock):
    """返回的 SRT 应保留原始时间轴。"""
    resp = client.post("/translate-srt", json={
        "filename": "test.srt",
        "content": SAMPLE_SRT,
    })
    text = resp.json()["translated_content"]
    assert "00:00:01,500 --> 00:00:05,000" in text
    assert "00:00:05,500 --> 00:00:09,000" in text


@patch("server.main.translate_blocks", side_effect=_fake_translated_blocks)
def test_translate_srt_renumbers(_mock):
    """返回的 SRT 应从 1 开始重新编号。"""
    resp = client.post("/translate-srt", json={
        "filename": "test.srt",
        "content": SAMPLE_SRT,
    })
    lines = resp.json()["translated_content"].strip().split("\n")
    assert lines[0] == "1"


def test_translate_srt_empty_content():
    """空内容应返回 422 或错误。"""
    resp = client.post("/translate-srt", json={
        "filename": "empty.srt",
        "content": "",
    })
    # 空内容解析不到字幕，应返回 400
    assert resp.status_code == 400


def test_translate_srt_missing_field():
    """缺少必填字段应返回 422。"""
    resp = client.post("/translate-srt", json={
        "filename": "x.srt",
        # content 缺失
    })
    assert resp.status_code == 422
