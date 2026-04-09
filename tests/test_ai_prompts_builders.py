# tests/test_ai_prompts_builders.py
from app.services.ai_prompts import (
    DEFAULT_SUMMARIZE_INSTRUCTIONS,
    DEFAULT_TRANSLATE_INSTRUCTIONS,
    SUMMARIZE_FIXED_SUFFIX,
    build_summarize_prompt,
    build_translate_prompt,
)


def test_build_summarize_prompt_default():
    prompt = build_summarize_prompt(None, "some article text")
    assert DEFAULT_SUMMARIZE_INSTRUCTIONS in prompt
    assert SUMMARIZE_FIXED_SUFFIX in prompt
    assert "some article text" in prompt
    assert "你是中文资讯编辑" in prompt


def test_build_summarize_prompt_custom():
    prompt = build_summarize_prompt("custom instructions", "some article text")
    assert "custom instructions" in prompt
    assert DEFAULT_SUMMARIZE_INSTRUCTIONS not in prompt
    assert SUMMARIZE_FIXED_SUFFIX in prompt
    assert "some article text" in prompt


def test_build_summarize_prompt_truncates_text():
    long_text = "x" * 7000
    prompt = build_summarize_prompt(None, long_text)
    # text is truncated to 6000 chars before appending
    assert "x" * 6000 in prompt
    assert "x" * 6001 not in prompt


def test_build_translate_prompt_default():
    prompt = build_translate_prompt(None, "My Article Title")
    assert DEFAULT_TRANSLATE_INSTRUCTIONS in prompt
    assert "My Article Title" in prompt
    assert "标题:" in prompt


def test_build_translate_prompt_custom():
    prompt = build_translate_prompt("自定义翻译指令", "My Article Title")
    assert "自定义翻译指令" in prompt
    assert DEFAULT_TRANSLATE_INSTRUCTIONS not in prompt
    assert "My Article Title" in prompt


def test_build_translate_prompt_truncates_title():
    long_title = "T" * 300
    prompt = build_translate_prompt(None, long_title)
    assert "T" * 200 in prompt
    assert "T" * 201 not in prompt
