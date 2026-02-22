import axios from 'axios'

export async function sendWeChatCard(webhookUrl: string, title: string, content: string) {
  if (!webhookUrl) {
    return { ok: false, error: 'missing_webhook' }
  }
  try {
    const payload = { msgtype: 'markdown', markdown: { content: `**${title}**\n\n${content}` } }
    const res = await axios.post(webhookUrl, payload, { timeout: 10000 })
    return { ok: true, status: res.status }
  } catch (e: any) {
    return { ok: false, error: String(e?.message || e) }
  }
}

