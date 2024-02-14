import pytest
from unittest.mock import MagicMock

from src.translator import Translator

@pytest.fixture
def translator():
    # 创建 Translator 实例，用于测试
    return Translator()

def test_init(translator):
    assert translator.model == "GPT-4-TURBO"
    assert translator.temperature == 0.5
    assert translator.llm is not None

def test_read_subtitle_file(translator, tmp_path):
    # 创建临时字幕文件
    file_path = tmp_path / "subtitle.srt"
    file_path.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello\n\n2\n00:00:03,000 --> 00:00:04,000\nWorld\n")
    
    # 测试读取字幕文件
    blocks = translator.read_subtitle_file(str(file_path))
    assert len(blocks) == 2
    assert blocks[0]['index'] == "1"
    assert blocks[0]['text'] == "Hello"
    assert blocks[1]['index'] == "2"
    assert blocks[1]['text'] == "World"

def test_translate(monkeypatch, translator):
    # 模拟 Azure LLM 的返回值
    mocked_response = MagicMock()
    mocked_response.data.choices[0].content.lstrip.return_value = "Translated text"
    monkeypatch.setattr(translator.llm, "completions", MagicMock(create=MagicMock(return_value=mocked_response)))
    
    # 测试翻译功能
    result = translator.translate("测试文本")
    assert result == "Translated text"

def test_translate_blocks(monkeypatch, translator):
    # 模拟 translate 方法
    translator.translate = MagicMock(return_value="Translated text")
    
    blocks = [{"index": "1", "timestamp": "00:00:01,000 --> 00:00:02,000", "text": "Hello"}]
    translated_blocks = translator.translate_blocks(blocks)
    assert len(translated_blocks) == 1
    assert translated_blocks[0]['text'] == "Hello\nTranslated text"

def test_write_subtitle_file(translator, tmp_path):
    # 准备翻译后的字幕块列表
    blocks = [{"index": "1", "timestamp": "00:00:01,000 --> 00:00:02,000", "text": "Hello\nTranslated Hello"}]
    
    # 创建临时文件路径
    file_path = tmp_path / "translated_subtitle.srt"
    translator.write_subtitle_file(blocks, str(file_path))
    
    # 验证文件内容
    expected_content = "1\n00:00:01,000 --> 00:00:02,000\nHello\nTranslated Hello\n\n"
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        assert content == expected_content
