"""命令行入口 —— 把所有模块串起来。"""

import sys
from typing import Optional

from openai import OpenAI

from .config import parse_args
from .errors import (
    ConfigError,
    FileNotFoundError_,
    FileReadError,
    InvalidFileTypeError,
    ParseError,
    SRTTranslatorError,
    TranslationError,
)
from .srt_parser import parse_srt, serialize_srt
from .translator import translate_blocks


def main(argv: Optional[list[str]] = None) -> None:
    """CLI 主入口。"""
    try:
        _run(argv)
    except (FileNotFoundError_, InvalidFileTypeError, ConfigError) as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(e.exit_code)
    except FileReadError as e:
        print(f"❌ 无法读取文件：{e}", file=sys.stderr)
        sys.exit(e.exit_code)
    except TranslationError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(e.exit_code)
    except SRTTranslatorError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(e.exit_code)


def _run(argv: Optional[list[str]] = None) -> None:
    cfg = parse_args(argv)

    # ---- 读取 ----
    try:
        raw = cfg.input_path.read_text(encoding="utf-8")
    except Exception as e:
        raise FileReadError(str(e)) from e

    # ---- 解析 ----
    blocks = parse_srt(raw)
    if not blocks:
        raise ParseError("未能从文件中解析到任何字幕条目")

    print(f"📖 解析到 {len(blocks)} 条字幕")
    if cfg.verbose:
        print(f"   输入：{cfg.input_path}")
        print(f"   输出：{cfg.output_path}")
        print(f"   模型：{cfg.model}")
        print(f"   批量：{cfg.batch_size} 条/次")

    # ---- 翻译 ----
    client_kwargs = {"api_key": cfg.api_key}
    if cfg.base_url:
        client_kwargs["base_url"] = cfg.base_url
    client = OpenAI(**client_kwargs)

    translated = translate_blocks(
        client,
        blocks,
        model=cfg.model,
        batch_size=cfg.batch_size,
        verbose=cfg.verbose,
    )

    # ---- 输出 ----
    output_text = serialize_srt(translated)
    cfg.output_path.write_text(output_text, encoding="utf-8")

    print(f"✅ 翻译完成 → {cfg.output_path}（共 {len(translated)} 条）")
