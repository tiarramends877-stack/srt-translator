"""SRT 字幕文件解析与序列化。"""

import re

# 匹配单条字幕的完整 block：编号 → 时间轴 → 一行或多行文本 → 空行
_SUB_RE = re.compile(
    r"^(\d+)\s*\n"
    r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*\n"
    r"((?:.+\n?)+?)(?=\n\d+\n|\Z)",
    re.MULTILINE,
)


def parse_srt(text: str) -> list[dict]:
    """解析 SRT 文本，返回字幕 block 列表。"""
    blocks = []
    for m in _SUB_RE.finditer(text):
        blocks.append({
            "index": int(m.group(1)),
            "start": m.group(2).replace(",", "."),
            "end": m.group(3).replace(",", "."),
            "text": m.group(4).strip(),
        })
    return blocks


def serialize_srt(blocks: list[dict]) -> str:
    """将字幕 block 列表序列化为 SRT 文本。"""
    lines = []
    for i, b in enumerate(blocks, start=1):
        lines.append(str(i))
        lines.append(f"{b['start']} --> {b['end']}".replace(".", ","))
        lines.append(b["text"])
        lines.append("")  # 空行分隔
    return "\n".join(lines)
