# app/services/ai_prompts.py

DEFAULT_SUMMARIZE_INSTRUCTIONS = """\
1) 用中文输出;
2) 生成3-6句高信息密度的正文，覆盖"发生了什么+背景+影响/所以怎样(so what)";
3) 至少标记两句为关键判断(boldIndices)，其中一条必须是"so what";
4) 同时提取3个关键要点;
5) 给出0-1之间的质量分数;\
"""

DEFAULT_TRANSLATE_INSTRUCTIONS = "将以下标题精准翻译为中文标题，保持简洁凝练"

SUMMARIZE_FIXED_SUFFIX = (
    '结果以以下JSON格式返回: { "sentences": string[], "boldIndices": number[], '
    '"keyPoints": string[], "qualityScore": number }\n原文内容: '
)


def build_summarize_prompt(instructions: str | None, text: str) -> str:
    """Build the full summarization prompt.

    The instruction block is user-configurable (stored in SystemConfig.summarize_prompt).
    The preamble and JSON schema contract are always fixed — editing them would break
    JSON parsing in ai.py.
    """
    block = instructions if instructions is not None else DEFAULT_SUMMARIZE_INSTRUCTIONS
    return (
        f"你是中文资讯编辑，按以下标准生成中文内容:\n{block}\n"
        f"{SUMMARIZE_FIXED_SUFFIX}{text[:6000]}"
    )


def build_translate_prompt(instructions: str | None, title: str) -> str:
    """Build the full title translation prompt.

    The instruction text is user-configurable. The title is always appended by code.
    """
    block = instructions if instructions is not None else DEFAULT_TRANSLATE_INSTRUCTIONS
    return f"{block}\n标题: {title[:200]}"
