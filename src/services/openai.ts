import OpenAI from 'openai'

export async function summarize(text: string) {
  const key = process.env.OPENAI_API_KEY
  if (!key) {
    return {
      summary: text.slice(0, 300),
      keyPoints: [],
      qualityScore: 0
    }
  }
  const client = new OpenAI({ apiKey: key })
  const prompt = [
    '你是中文资讯编辑，按以下标准生成中文内容：',
    '1) 用中文输出；',
    '2) 生成3-6句高信息密度的正文，覆盖“发生了什么+背景+影响/所以怎样(so what)”；',
    '3) 至少标记两句为关键判断（boldIndices），其中一条必须是“so what”；',
    '4) 同时提取3个关键要点；',
    '5) 给出0-1之间的质量分数；',
    '返回严格JSON：{ "sentences": string[], "boldIndices": number[], "keyPoints": string[], "qualityScore": number }',
    `原文内容: ${text.slice(0, 6000)}`
  ].join('\n')
  const resp = await client.chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [{ role: 'user', content: prompt }],
    temperature: 0.3
  })
  const out = resp.choices[0]?.message?.content || ''
  try {
    const parsed = JSON.parse(out)
    return {
      summary: Array.isArray(parsed.sentences) ? String(parsed.sentences.join('')) : String(parsed.summary || ''),
      sentences: Array.isArray(parsed.sentences) ? parsed.sentences.map(String) : undefined,
      boldIndices: Array.isArray(parsed.boldIndices) ? parsed.boldIndices.map((n: any) => Number(n)) : undefined,
      keyPoints: Array.isArray(parsed.keyPoints) ? parsed.keyPoints.map(String) : [],
      qualityScore: Number(parsed.qualityScore || 0)
    }
  } catch {
    return {
      summary: out.slice(0, 300),
      keyPoints: [],
      qualityScore: 0.5
    }
  }
}

export async function translateTitleToZh(title: string) {
  const key = process.env.OPENAI_API_KEY
  if (!key) return title
  const client = new OpenAI({ apiKey: key })
  const prompt = `将以下标题精准翻译为中文标题，保持简洁凝练：${title.slice(0, 200)}`
  const resp = await client.chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [{ role: 'user', content: prompt }],
    temperature: 0
  })
  const out = resp.choices[0]?.message?.content || ''
  return out.trim() || title
}
