"""FastAPI 服务 —— 将 SRT 翻译能力暴露为 HTTP API。"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel

# 确保项目根目录在 sys.path 中
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from srt_translator.config import get_output_path  # noqa: E402
from srt_translator.errors import ParseError, TranslationError  # noqa: E402
from srt_translator.srt_parser import parse_srt, serialize_srt  # noqa: E402
from srt_translator.translator import translate_blocks  # noqa: E402

load_dotenv()

# ---------------------------------------------------------------------------
# 模型
# ---------------------------------------------------------------------------


class TranslateRequest(BaseModel):
    filename: str
    content: str


class TranslateResponse(BaseModel):
    output_filename: str
    translated_content: str


# ---------------------------------------------------------------------------
# 依赖
# ---------------------------------------------------------------------------


def _build_client() -> OpenAI:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY 未设置")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    return OpenAI(api_key=api_key, base_url=base_url)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="SRT Translator", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/translate-srt", response_model=TranslateResponse)
def translate_srt(req: TranslateRequest):
    """接收英文 SRT 内容和文件名，返回中文 SRT。"""
    # 解析
    try:
        blocks = parse_srt(req.content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SRT 解析失败：{e}")
    if not blocks:
        raise HTTPException(status_code=400, detail="未能从请求内容中解析到任何字幕条目")

    # 翻译
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    client = _build_client()
    translated = translate_blocks(client, blocks, model=model)

    # 序列化
    output_text = serialize_srt(translated)

    # 输出文件名
    output_name = str(get_output_path(Path(req.filename)))

    return TranslateResponse(
        output_filename=output_name,
        translated_content=output_text,
    )


# ---------------------------------------------------------------------------
# 启动
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
