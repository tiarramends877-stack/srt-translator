# SRT 字幕翻译工具

将英文 `.srt` 字幕文件翻译为简体中文，使用 DeepSeek API（兼容 OpenAI SDK）。

## 快速开始

```bash
# 1. 安装依赖
pip install -e .        # 生产依赖
# 或
pip install -r requirements.txt

# 2. 配置 DeepSeek API Key
cp .env.example .env
# 编辑 .env 填入真实 key

# 3. 翻译
python translate.py sample.en.srt
# → 输出 sample.zh.srt
```

## DeepSeek 配置

在 `.env` 中设置：

```env
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
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
python translate.py movie.srt \
  --base-url https://api.openai.com/v1 \
  --model gpt-4o-mini \
  --api-key sk-your-openai-key
```

## API 服务

启动本地 FastAPI 服务，通过 HTTP 接口翻译字幕：

```bash
# 启动服务（开发模式，热重载）
python server/main.py
# → http://localhost:8000
```

### POST /translate-srt

请求体（JSON）：

```json
{
  "filename": "example.en.srt",
  "content": "1\n00:00:01,500 --> 00:00:05,000\nHello everyone.\n"
}
```

响应体（JSON）：

```json
{
  "output_filename": "example.zh.srt",
  "translated_content": "1\n00:00:01,500 --> 00:00:05,000\n大家好。\n"
}
```

交互式文档：启动后访问 `http://localhost:8000/docs`

## Chrome 扩展

通过浏览器插件直接上传 `.srt` 文件并下载翻译结果。

### 加载扩展

1. 确保本地服务已启动：`python server/main.py`
2. 打开 Chrome → `chrome://extensions`
3. 右上角开启 **Developer mode**
4. 点击 **Load unpacked** → 选择 `extension/` 目录
5. 点击工具栏上的扩展图标即可使用

### 使用流程

1. 点击 Choose .srt file → 选择英文 `.srt`
2. 点击 **Translate** → 等待翻译完成
3. 点击 **Download .zh.srt** → 保存中文翻译文件

如果本地 API 未启动，会显示「Please start the local server first」。

## 测试

```bash
pytest
# 20 passed — 包括 SRT 解析、序列化、输出文件名、API 端点
```

本项目已用 76 条字幕的真实 `.srt` 文件测试通过，
翻译质量良好，编号和时间轴完整保留。

## 项目结构

```
├── translate.py                # 入口（薄封装）
├── srt_translator/             # 核心包
│   ├── __init__.py
│   ├── cli.py                  # 命令行入口 + 错误提示
│   ├── config.py               # 环境变量 + 命令行参数
│   ├── errors.py               # 自定义错误类型
│   ├── srt_parser.py           # SRT 解析 / 序列化
│   └── translator.py           # DeepSeek API 翻译
├── server/                     # FastAPI 服务
│   └── main.py                 # POST /translate-srt
├── extension/                  # Chrome 扩展 (Manifest V3)
│   ├── manifest.json
│   ├── popup.html
│   └── popup.js
├── tests/                      # 测试
│   ├── test_srt_parser.py      # 解析 / 序列化测试
│   ├── test_output_filename.py # 输出文件名测试
│   └── test_server.py          # API 端点测试
├── pyproject.toml              # 项目配置 + 依赖
├── requirements.txt            # pip 依赖（简洁版）
├── .env.example                # 环境变量模板
└── README.md
```

## 运行测试

```bash
# 安装开发依赖
pip install -e ".[dev]"
# 或
pip install pytest

# 运行测试
pytest
```

## 依赖

- Python ≥ 3.9
- `openai` — OpenAI Python SDK（DeepSeek 兼容）
- `python-dotenv` — .env 文件加载
- `pytest` — 测试框架（开发依赖）
