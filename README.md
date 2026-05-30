# SRT 字幕翻译工具

将英文 `.srt` 字幕文件翻译为简体中文，使用 DeepSeek API（兼容 OpenAI SDK）。

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 DeepSeek API Key（任选一种）
cp .env.example .env          # 然后编辑 .env 填入真实 key
# 或
export DEEPSEEK_API_KEY=sk-xxx

# 3. 翻译
python translate.py sample.en.srt
# → 输出 sample.zh.srt
```

## DeepSeek 配置

在 `.env` 中设置：

```env
DEEPSEEK_API_KEY=sk-your-deepseek-api-key    # 必填
DEEPSEEK_BASE_URL=https://api.deepseek.com    # 可选，默认值
DEEPSEEK_MODEL=deepseek-chat                  # 可选，默认值
```

也可以使用命令行参数覆盖：

```bash
python translate.py input.srt \
  --api-key sk-xxx \
  --base-url https://api.deepseek.com \
  --model deepseek-chat
```

## 用法

```
python translate.py <输入.srt> [选项]

参数：
  input                 输入 .srt 文件路径

选项：
  -o, --output PATH     输出文件路径（默认：<输入>.zh.srt）
  --model NAME          模型名称（默认：deepseek-chat）
  --batch-size N        每批翻译条数（默认：20）
  --api-key KEY         DeepSeek API Key
  --base-url URL        自定义 API 地址
  -v, --verbose         显示详细进度
```

## 示例

```bash
# 基础用法
python translate.py movie.en.srt

# 指定输出文件和模型
python translate.py movie.en.srt -o movie.zh.srt --model deepseek-chat

# 增大批量、减少 API 调用次数
python translate.py movie.en.srt --batch-size 30 -v

# 兼容 OpenAI 或其他兼容 API
python translate.py movie.en.srt \
  --base-url https://api.openai.com/v1 \
  --model gpt-4o-mini \
  --api-key sk-your-openai-key
```

## 项目结构

```
├── translate.py       # 主程序
├── requirements.txt   # Python 依赖
├── .env.example       # 环境变量模板
└── README.md          # 本文件
```

## 依赖

- Python ≥ 3.9
- `openai` — OpenAI Python SDK（DeepSeek 兼容）
- `python-dotenv` — .env 文件加载
