import axios from 'axios'

export async function sendPushPlus(token: string, title: string, html: string) {
  if (!token) return { ok: false, error: 'missing_token' }
  try {
    const res = await axios.post('https://www.pushplus.plus/send', {
      token,
      title,
      content: html,
      template: 'html'
    }, { timeout: 10000 })
    const ok = res.data?.code === 200
    return ok ? { ok: true, status: res.status } : { ok: false, error: String(res.data?.msg || 'unknown') }
  } catch (e: any) {
    return { ok: false, error: String(e?.message || e) }
  }
}

