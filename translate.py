#!/usr/bin/env python3
"""
SRT Subtitle Translator (EN → 简体中文)
使用 DeepSeek API 将英文字幕翻译为简体中文，保留原始编号和时间轴。
基于 OpenAI SDK 兼容方式调用。
"""

import argparse
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


# ---------------------------------------------------------------------------
# SRT 解析 / 序列化
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 翻译
# ---------------------------------------------------------------------------

# 批量翻译时的分隔符（选一个不太可能出现在字幕中的字符串）
_SEPARATOR = "\n---SPLIT---\n"


def translate_blocks(
    client: OpenAI,
    blocks: list[dict],
    model: str,
    batch_size: int = 20,
    verbose: bool = False,
) -> list[dict]:
    """
    批量翻译字幕文本。每次发送 batch_size 条字幕，
    用分隔符拼接，要求模型原样返回分隔的结构。
    """
    result: list[dict] = []
    total = len(blocks)

    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch = blocks[batch_start:batch_end]

        # 构建待翻译文本（每条一行，分隔符隔开）
        source_texts = [b["text"] for b in batch]
        payload = _SEPARATOR.join(source_texts)

        prompt = (
            "你是一个专业字幕翻译器。请将以下英文字幕逐条翻译为简体中文。\n"
            "规则：\n"
            "1. 保留原文的语气、风格和换行\n"
            "2. 专有名词、技术术语尽量保留原文或使用通用译名\n"
            "3. 每条翻译独立，不要添加上下文或注释\n"
            "4. 保持与原文一致的条目数量和顺序\n"
            "5. 用 \\n---SPLIT---\\n 分隔每条翻译，不要添加额外编号\n\n"
            f"{payload}"
        )

        if verbose:
            print(
                f"  [翻译中] 第 {batch_start + 1}-{batch_end} / {total} 条 ...",
                file=sys.stderr,
            )

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个专业的中英字幕翻译助手。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
        except Exception as e:
            print(f"❌ API 请求失败：{e}", file=sys.stderr)
            sys.exit(1)

        translated_text = response.choices[0].message.content.strip()

        # 按分隔符切分回单条
        translated_parts = translated_text.split(_SEPARATOR.strip())

        # 如果切分数量不匹配，尝试用更宽松的方式
        if len(translated_parts) != len(source_texts):
            translated_parts = [s.strip() for s in translated_text.split("\n---SPLIT---\n")]

        if len(translated_parts) != len(source_texts):
            print(
                f"  ⚠ 警告：第 {batch_start + 1} 批翻译条目数不匹配 "
                f"(期望 {len(source_texts)}，实际 {len(translated_parts)})，"
                f"已回退为逐条翻译",
                file=sys.stderr,
            )
            # 回退：逐条翻译这一批
            for b in batch:
                single = _translate_single(client, b, model, verbose=False)
                result.append(single)
            continue

        for b, zh_text in zip(batch, translated_parts):
            result.append({
                "index": b["index"],
                "start": b["start"],
                "end": b["end"],
                "text": zh_text.strip(),
            })

    return result


def _translate_single(
    client: OpenAI,
    block: dict,
    model: str,
    verbose: bool = False,
) -> dict:
    """逐条翻译（回退方案）。"""
    if verbose:
        print(f"  [逐条翻译] #{block['index']}", file=sys.stderr)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个专业的中英字幕翻译助手。将英文翻译为简体中文，保持语气和风格。"},
                {"role": "user", "content": f"翻译为简体中文：\n{block['text']}"},
            ],
            temperature=0.3,
        )
    except Exception as e:
        print(f"❌ API 请求失败（#{block['index']}）：{e}", file=sys.stderr)
        sys.exit(1)
    zh_text = response.choices[0].message.content.strip()
    return {
        "index": block["index"],
        "start": block["start"],
        "end": block["end"],
        "text": zh_text,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="SRT 英文字幕 → 简体中文翻译工具（DeepSeek API / OpenAI 兼容）",
    )
    parser.add_argument(
        "input",
        type=str,
        help="输入 .srt 文件路径",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="输出文件路径（默认：<输入文件名>.zh.srt）",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        help="模型名称（默认：deepseek-chat，可通过 DEEPSEEK_MODEL 环境变量设置）",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="每批翻译的字幕条数（默认：20）",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API Key（也可通过 DEEPSEEK_API_KEY 环境变量设置）",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="API Base URL（默认：https://api.deepseek.com，也可通过 DEEPSEEK_BASE_URL 环境变量设置）",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细进度",
    )

    args = parser.parse_args()

    # ---- 输入文件检查 ----
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ 文件不存在：{input_path}", file=sys.stderr)
        sys.exit(1)
    if input_path.suffix.lower() != ".srt":
        print(f"❌ 错误：文件扩展名必须是 .srt，实际为 {input_path.suffix}", file=sys.stderr)
        sys.exit(1)

    # ---- API Key ----
    api_key = args.api_key or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ 未设置 API Key。请通过以下方式之一提供：", file=sys.stderr)
        print("   1. 命令行：--api-key <key>", file=sys.stderr)
        print("   2. 环境变量：export DEEPSEEK_API_KEY=<key>", file=sys.stderr)
        print("   3. .env 文件：DEEPSEEK_API_KEY=<key>", file=sys.stderr)
        sys.exit(1)

    base_url = args.base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    # ---- 输出路径 ----
    if args.output:
        output_path = Path(args.output)
    else:
        stem = input_path.stem  # e.g. "example.en" or "movie"
        if stem.endswith(".en"):
            stem = stem[:-3]    # "example.en" → "example"
        output_path = input_path.with_name(f"{stem}.zh.srt")

    # ---- 读取 & 解析 ----
    try:
        raw = input_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"❌ 无法读取文件：{e}", file=sys.stderr)
        sys.exit(1)
    blocks = parse_srt(raw)

    if not blocks:
        print("❌ 未能从文件中解析到任何字幕条目", file=sys.stderr)
        sys.exit(1)

    print(f"📖 解析到 {len(blocks)} 条字幕")
    if args.verbose:
        print(f"   输入：{input_path}")
        print(f"   输出：{output_path}")
        print(f"   模型：{args.model}")
        print(f"   批量：{args.batch_size} 条/次")

    # ---- 翻译 ----
    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = OpenAI(**client_kwargs)

    translated = translate_blocks(
        client,
        blocks,
        model=args.model,
        batch_size=args.batch_size,
        verbose=args.verbose,
    )

    # ---- 输出 ----
    output_text = serialize_srt(translated)
    output_path.write_text(output_text, encoding="utf-8")

    print(f"✅ 翻译完成 → {output_path}（共 {len(translated)} 条）")


if __name__ == "__main__":
    main()
