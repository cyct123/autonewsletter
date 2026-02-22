import axios from 'axios'

export async function sendLarkCard(webhookUrl: string, title: string, content: string) {
  if (!webhookUrl) {
    return { ok: false, error: 'missing_webhook' }
  }
  try {
    const payload = {
      msg_type: 'interactive',
      card: {
        elements: [{ tag: 'div', text: { tag: 'lark_md', content } }],
        header: { title: { tag: 'plain_text', content: title } }
      }
    }
    const res = await axios.post(webhookUrl, payload, { timeout: 10000 })
    return { ok: true, status: res.status }
  } catch (e: any) {
    return { ok: false, error: String(e?.message || e) }
  }
}

