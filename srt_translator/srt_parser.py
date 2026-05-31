"""SRT 字幕文件解析与序列化。"""

import re

# 每条字幕 block 内部：第一行编号，第二行时间轴，之后是文本
_BLOCK_RE = re.compile(
    r"^(\d+)[ \t]*\n"
    r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})[ \t]*-->[ \t]*"
    r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})[ \t]*\n"
    r"([\s\S]+)",
)


def parse_srt(text: str) -> list[dict]:
    """解析 SRT 文本，返回字幕 block 列表。"""
    # 统一行尾为 LF（兼容 Windows CRLF）
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    blocks: list[dict] = []

    # 按连续空行拆成 block
    raw_blocks = re.split(r"\n{2,}", text.strip())

    for raw in raw_blocks:
        raw = raw.strip()
        if not raw:
            continue

        m = _BLOCK_RE.match(raw)
        if not m:
            continue

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
