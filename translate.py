#!/usr/bin/env python3
"""SRT Subtitle Translator — thin CLI entry point."""

import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中，支持任意位置运行
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from srt_translator.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
