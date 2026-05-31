"""读取环境变量和命令行参数，产出配置字典。"""

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from .errors import ConfigError, FileNotFoundError_, InvalidFileTypeError


@dataclass
class Config:
    input_path: Path
    output_path: Path
    api_key: str
    base_url: str
    model: str
    batch_size: int
    verbose: bool


def get_output_path(input_path: Path, output_arg: Optional[str] = None) -> Path:
    """根据输入文件路径和可选的 --output 参数，计算输出路径。"""
    if output_arg:
        return Path(output_arg)

    stem = input_path.stem  # e.g. "example.en" or "movie"
    if stem.endswith(".en"):
        stem = stem[:-3]    # "example.en" → "example"
    return input_path.with_name(f"{stem}.zh.srt")


def parse_args(argv: Optional[list[str]] = None) -> Config:
    """解析命令行参数 + 环境变量，返回 Config。"""
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

    args = parser.parse_args(argv)

    # ---- 输入文件检查 ----
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError_(f"文件不存在：{input_path}")
    if input_path.suffix.lower() != ".srt":
        raise InvalidFileTypeError(
            f"文件扩展名必须是 .srt，实际为 {input_path.suffix}"
        )

    # ---- API Key ----
    api_key = args.api_key or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ConfigError(
            "未设置 API Key。请通过以下方式之一提供：\n"
            "  1. 命令行：--api-key <key>\n"
            "  2. 环境变量：export DEEPSEEK_API_KEY=<key>\n"
            "  3. .env 文件：DEEPSEEK_API_KEY=<key>"
        )

    base_url = args.base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    # ---- 输出路径 ----
    output_path = get_output_path(input_path, args.output)

    return Config(
        input_path=input_path,
        output_path=output_path,
        api_key=api_key,
        base_url=base_url,
        model=args.model,
        batch_size=args.batch_size,
        verbose=args.verbose,
    )
