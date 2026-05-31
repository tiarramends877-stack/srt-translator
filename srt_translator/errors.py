"""自定义错误类型。"""


class SRTTranslatorError(Exception):
    """所有自定义异常的基类。"""
    exit_code = 1


class FileNotFoundError_(SRTTranslatorError):
    """输入文件不存在。"""


class InvalidFileTypeError(SRTTranslatorError):
    """文件扩展名不是 .srt。"""


class ConfigError(SRTTranslatorError):
    """配置缺失（如 API Key）。"""


class FileReadError(SRTTranslatorError):
    """文件读取失败。"""


class ParseError(SRTTranslatorError):
    """SRT 解析失败（未找到任何字幕条目）。"""


class TranslationError(SRTTranslatorError):
    """API 请求失败。"""
