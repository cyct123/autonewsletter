import re
from typing import List, Dict, Set
import html


def build_newsletter_html(items: List[Dict]) -> str:
    """Build HTML newsletter from content items"""
    rows = []
    for item in items:
        sentences = to_sentences(item.get("summary", ""))[:6]
        bold_idx = pick_bold_indices(sentences)

        body_parts = []
        for i, s in enumerate(sentences[:max(3, min(6, len(sentences)))]):
            if i in bold_idx:
                body_parts.append(f"<strong>{escape_html(s)}</strong>")
            else:
                body_parts.append(escape_html(s))
        body = " ".join(body_parts)

        points = ""
        if item.get("key_points"):
            points_html = "".join([f"<li>{escape_html(p)}</li>" for p in item["key_points"]])
            points = f"<ul>{points_html}</ul>"

        quality_score = item.get("quality_score", 0)
        original_url = item.get("original_url", "")
        title = item.get("title", "")

        row = f"""
    <div style="padding:16px;border-bottom:1px solid #e5e7eb">
      <h3 style="color:#1e3a8a;margin:0 0 8px 0;">{escape_html(title)}</h3>
      <p style="margin:0 0 8px 0;">{body}</p>
      {points}
      <p style="margin:8px 0 0 0;font-size:12px;color:#64748b;">质量分数：{quality_score:.2f} · <a href="{escape_attr(original_url)}" style="color:#1e3a8a">原文链接</a></p>
    </div>"""
        rows.append(row)

    rows_html = "".join(rows) if rows else "<p>本周暂无内容</p>"

    return f"""
  <div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:#ffffff;color:#0f172a;">
    <div style="max-width:720px;margin:0 auto;padding:24px">
      <h2 style="color:#1e3a8a;margin:0 0 16px 0;">每周智能内容简报</h2>
      {rows_html}
      <p style="margin-top:24px;font-size:12px;color:#94a3b8;">此邮件由系统自动发送</p>
    </div>
  </div>
  """


def escape_html(s: str) -> str:
    """Escape HTML special characters"""
    return html.escape(s)


def escape_attr(s: str) -> str:
    """Escape HTML attribute value"""
    return s.replace('"', '&quot;')


def to_sentences(s: str) -> List[str]:
    """Split text into sentences"""
    # Split by Chinese/English punctuation followed by optional whitespace
    # Use a simpler approach without lookbehind
    parts = re.split(r'[。！？!?]\s*', s)
    parts = [t.strip() for t in parts if t.strip()]

    if len(parts) >= 3:
        return parts

    # If we got results, return them
    if parts:
        return parts

    # Fallback: return original string if no splits worked
    return [s.strip()] if s.strip() else []


def pick_bold_indices(sentences: List[str]) -> Set[int]:
    """Pick indices of sentences to bold"""
    bold_set = set()

    # Always bold first sentence
    if sentences:
        bold_set.add(0)

    # Find "so what" sentence
    pattern = re.compile(r'(这意味着|意味着|所以|因此|为何重要|重要|影响|带来|风险|机会)')
    for i, s in enumerate(sentences):
        if pattern.search(s):
            bold_set.add(i)
            break

    # Ensure at least 2 sentences are bolded
    if len(bold_set) < 2 and len(sentences) > 1:
        bold_set.add(1)

    return bold_set
