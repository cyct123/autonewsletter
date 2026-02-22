import type { ContentItem } from '../modules/content/index.js'

export function buildNewsletterHtml(items: ContentItem[]) {
  const rows = items.map((it) => {
    const sentences = toSentences(it.summary).slice(0, 6)
    const boldIdx = pickBoldIndices(sentences)
    const body = sentences
      .slice(0, Math.max(3, Math.min(6, sentences.length)))
      .map((s, i) => boldIdx.has(i) ? `<strong>${escapeHtml(s)}</strong>` : escapeHtml(s))
      .join(' ')
    const points = it.keyPoints?.length ? `<ul>${it.keyPoints.map(p => `<li>${escapeHtml(p)}</li>`).join('')}</ul>` : ''
    return `
    <div style="padding:16px;border-bottom:1px solid #e5e7eb">
      <h3 style="color:#1e3a8a;margin:0 0 8px 0;">${escapeHtml(it.title)}</h3>
      <p style="margin:0 0 8px 0;">${body}</p>
      ${points}
      <p style="margin:8px 0 0 0;font-size:12px;color:#64748b;">质量分数：${(it.qualityScore).toFixed(2)} · <a href="${escapeAttr(it.originalUrl)}" style="color:#1e3a8a">原文链接</a></p>
    </div>`
  }).join('')
  return `
  <div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:#ffffff;color:#0f172a;">
    <div style="max-width:720px;margin:0 auto;padding:24px">
      <h2 style="color:#1e3a8a;margin:0 0 16px 0;">每周智能内容简报</h2>
      ${rows || '<p>本周暂无内容</p>'}
      <p style="margin-top:24px;font-size:12px;color:#94a3b8;">此邮件由系统自动发送</p>
    </div>
  </div>
  `
}

function escapeHtml(s: string) {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}
function escapeAttr(s: string) {
  return s.replace(/"/g, '&quot;')
}

function toSentences(s: string): string[] {
  const parts = s
    .split(/(?<=[。！？!?]|\\.)\\s+/g)
    .map(t => t.trim())
    .filter(Boolean)
  if (parts.length >= 3) return parts
  const byPunct = s.split(/[。！？!?]/g).map(t => t.trim()).filter(Boolean)
  return byPunct.length ? byPunct : [s.trim()].filter(Boolean)
}

function pickBoldIndices(sentences: string[]): Set<number> {
  const set = new Set<number>()
  if (sentences.length) set.add(0)
  const idx = sentences.findIndex(s => /(这意味着|意味着|所以|因此|为何重要|重要|影响|带来|风险|机会)/.test(s))
  if (idx >= 0) set.add(idx)
  if (set.size < 2 && sentences.length > 1) set.add(1)
  return set
}
