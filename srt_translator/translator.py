"""调用 DeepSeek API 翻译字幕文本。"""

import sys

from openai import OpenAI

from .errors import TranslationError

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
            raise TranslationError(  # noqa: F821
                f"API 请求失败：{e}"
            ) from e

        translated_text = response.choices[0].message.content.strip()
        # 清理模型可能在末尾追加的分隔符
        translated_text = translated_text.rstrip().rstrip(_SEPARATOR.strip())

        # 按分隔符切分回单条，清理残留
        translated_parts = translated_text.split(_SEPARATOR.strip())
        translated_parts = [s.strip().strip("\\n") for s in translated_parts]

        # 如果切分数量不匹配，尝试用更宽松的方式
        if len(translated_parts) != len(source_texts):
            translated_parts = [s.strip().strip("\\n") for s in translated_text.split("\n---SPLIT---\n")]

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
        raise TranslationError(  # noqa: F821
            f"API 请求失败（#{block['index']}）：{e}"
        ) from e

    zh_text = response.choices[0].message.content.strip()
    return {
        "index": block["index"],
        "start": block["start"],
        "end": block["end"],
        "text": zh_text,
    }
