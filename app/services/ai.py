# app/services/ai.py
import json
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI
from app.config import settings
from app.repositories.system_config import get_system_config
from app.services.ai_prompts import build_summarize_prompt, build_translate_prompt
from app.utils.logger import logger


async def summarize(text: str, db: AsyncSession) -> dict:
    """Generate Chinese summary with key points and quality score"""
    config = await get_system_config(db)

    if config.ai_model == "openai" and settings.openai_api_key:
        api_key = settings.openai_api_key
        base_url = None
        model = "gpt-4o-mini"
    elif settings.deepseek_api_key:
        if config.ai_model == "openai":
            logger.warning("ai_model_fallback", configured="openai", reason="OPENAI_API_KEY not set, using DeepSeek")
        api_key = settings.deepseek_api_key
        base_url = "https://api.deepseek.com"
        model = "deepseek-chat"
    else:
        logger.warning("no_api_key_configured", message="Neither DEEPSEEK_API_KEY nor OPENAI_API_KEY is set")
        return {
            "summary": text[:300],
            "sentences": [],
            "boldIndices": [],
            "keyPoints": [],
            "qualityScore": 0,
        }

    logger.info("summarize_called", text_length=len(text), using_custom_prompt=config.summarize_prompt is not None)
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    prompt = build_summarize_prompt(config.summarize_prompt, text)

    logger.info("ai_request_starting", model=model, prompt_length=len(prompt))

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        output = response.choices[0].message.content
        logger.info("ai_response_received", model=model, output_length=len(output), output_preview=output[:200])

        parsed = json.loads(output)
        result = {
            "summary": "".join(parsed.get("sentences", [])),
            "sentences": parsed.get("sentences", []),
            "boldIndices": parsed.get("boldIndices", []),
            "keyPoints": parsed.get("keyPoints", []),
            "qualityScore": float(parsed.get("qualityScore", 0))
        }
        logger.info("ai_summarization_success", model=model, quality_score=result["qualityScore"], key_points_count=len(result["keyPoints"]))
        return result
    except json.JSONDecodeError as e:
        logger.error("ai_json_parse_failed", error=str(e), output=output[:500] if 'output' in locals() else "N/A")
        return {
            "summary": text[:300],
            "sentences": [],
            "boldIndices": [],
            "keyPoints": [],
            "qualityScore": 0.5
        }
    except Exception as e:
        logger.error("ai_summarization_failed", error=str(e), error_type=type(e).__name__, exc_info=True)
        return {
            "summary": text[:300],
            "sentences": [],
            "boldIndices": [],
            "keyPoints": [],
            "qualityScore": 0.5
        }


async def translate_title(title: str, db: AsyncSession) -> str:
    """Translate English title to Chinese"""
    ascii_count = sum(1 for c in title if ord(c) < 128)
    ascii_ratio = ascii_count / max(len(title), 1)

    config = await get_system_config(db)
    logger.info("translate_title_called", title=title[:100], ascii_ratio=ascii_ratio, using_custom_prompt=config.translate_prompt is not None)

    if ascii_ratio < 0.6:
        logger.info("translation_skipped", reason="already_chinese", ascii_ratio=ascii_ratio)
        return title

    if config.ai_model == "openai" and settings.openai_api_key:
        api_key = settings.openai_api_key
        base_url = None
        model = "gpt-4o-mini"
    elif settings.deepseek_api_key:
        if config.ai_model == "openai":
            logger.warning("ai_model_fallback", configured="openai", reason="OPENAI_API_KEY not set, using DeepSeek")
        api_key = settings.deepseek_api_key
        base_url = "https://api.deepseek.com"
        model = "deepseek-chat"
    else:
        logger.warning("translation_skipped_no_api_key")
        return title

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    prompt = build_translate_prompt(config.translate_prompt, title)

    try:
        logger.info("translation_request_starting", model=model)
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        translated = response.choices[0].message.content.strip()
        logger.info("translation_success", original=title, translated=translated)
        return translated or title
    except Exception as e:
        logger.error("title_translation_failed", error=str(e), error_type=type(e).__name__, exc_info=True)
        return title
