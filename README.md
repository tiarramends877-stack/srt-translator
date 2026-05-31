# SRT Translator

将英文 `.srt` 字幕文件翻译为简体中文，基于 DeepSeek API（兼容 OpenAI SDK）。

提供三种使用方式：**命令行**、**本地 API 服务**、**Chrome 浏览器插件**。

## Features

- 解析标准 `.srt` 字幕，保留编号和时间轴不变
- 批量翻译，可配置每批条数，减少 API 调用
- 自动处理 Windows CRLF 行尾
- 多行字幕换行保留
- 输出文件名智能生成：`movie.en.srt` → `movie.zh.srt`，`subtitles.srt` → `subtitles.zh.srt`
- 兼容 DeepSeek、OpenAI 以及任何 OpenAI 兼容 API
- 完整的 pytest 测试覆盖（20 个测试）

## 项目结构

```
├── translate.py                 # CLI 入口
├── srt_translator/              # 核心翻译引擎
│   ├── cli.py                   #   命令行入口 + 错误处理
│   ├── config.py                #   环境变量 / CLI 参数解析
│   ├── errors.py                #   自定义异常类型
│   ├── srt_parser.py            #   SRT 解析 / 序列化
│   └── translator.py            #   DeepSeek API 批量翻译
├── server/
│   └── main.py                  # FastAPI 服务：POST /translate-srt
├── extension/                   # Chrome 插件 (Manifest V3)
│   ├── manifest.json
│   ├── popup.html
│   └── popup.js
├── tests/
│   ├── test_srt_parser.py
│   ├── test_output_filename.py
│   └── test_server.py
├── pyproject.toml
├── requirements.txt
├── .env.example
└── example.en.srt               # 示例字幕
```

## Quick Start

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 3. 翻译
python translate.py example.en.srt -v
# → 输出 example.zh.srt
```

## DeepSeek API Key 配置

在项目根目录创建 `.env` 文件：

```env
DEEPSEEK_API_KEY=sk-your-deepseek-api-key    # 必填
DEEPSEEK_BASE_URL=https://api.deepseek.com    # 可选
DEEPSEEK_MODEL=deepseek-chat                  # 可选
```

也可通过命令行参数覆盖：

```bash
python translate.py input.srt \
  --api-key sk-xxx \
  --base-url https://api.deepseek.com \
  --model deepseek-chat
```

## CLI 使用方法

```bash
python translate.py <输入.srt> [选项]

选项：
  -o, --output PATH     输出文件路径（默认：自动生成 .zh.srt）
  --model NAME          模型名称（默认：deepseek-chat）
  --batch-size N        每批翻译条数（默认：20）
  --api-key KEY         API Key
  --base-url URL        自定义 API 地址
  -v, --verbose         显示详细进度
```

```bash
# 基础用法
python translate.py movie.srt

# 使用 OpenAI
python translate.py movie.srt \
  --base-url https://api.openai.com/v1 \
  --model gpt-4o-mini \
  --api-key sk-your-key
```

## 本地 FastAPI 服务

在项目根目录启动：

```bash
python server/main.py
# → http://localhost:8000
# → 交互式文档：http://localhost:8000/docs
```

### POST /translate-srt

```json
// Request
{
  "filename": "example.en.srt",
  "content": "1\n00:00:01,500 --> 00:00:05,000\nHello everyone.\n"
}

// Response
{
  "output_filename": "example.zh.srt",
  "translated_content": "1\n00:00:01,500 --> 00:00:05,000\n大家好。\n"
}
```

## Chrome 插件

通过浏览器按钮上传 `.srt` 文件并下载翻译结果，无需离开浏览器。

### 加载插件

1. 打开 Chrome，地址栏输入 `chrome://extensions`
2. 右上角开启 **Developer mode**
3. 点击 **Load unpacked**
4. 选择项目中的 `extension/` 目录
5. 工具栏出现插件图标，点击即可使用

> *(插件截图：popup 窗口显示 3 步说明、文件选择按钮、Translate 按钮和 Download 按钮)*

### 使用方法

> ⚠️ 先启动本地 server：`python server/main.py`

1. 点击工具栏 **SRT Translator** 图标
2. 点击 **Choose .srt file**，选择英文 `.srt` 文件
3. 点击 **Translate**，等待翻译完成
4. 点击 **Download .zh.srt**，保存中文翻译

如果本地 API 未启动，插件会显示：**Please start the local server first**。

## 测试

```bash
pip install pytest
pytest
# 20 passed — SRT 解析、序列化、文件名生成、API 端点
```

## 安全提醒

**不要提交 `.env` 文件！** 它已在 `.gitignore` 中。`.env.example` 是模板，可以安全提交。

## 当前限制

- 仅支持 `.srt` 格式字幕文件
- Chrome 插件不自动读取 YouTube 字幕
- 不做视频字幕覆盖注入
- Chrome 插件依赖本地 server 运行

## Roadmap

- [ ] Web UI
- [ ] YouTube 字幕自动读取
- [ ] 字幕实时预览
- [ ] 多语言翻译支持
- [ ] 自定义翻译术语表
- [ ] 批量文件翻译
