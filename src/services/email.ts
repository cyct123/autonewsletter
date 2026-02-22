import nodemailer from 'nodemailer'

export async function sendEmailHtml(to: string, subject: string, html: string) {
  const host = process.env.SMTP_HOST || ''
  const port = Number(process.env.SMTP_PORT || 465)
  const user = process.env.SMTP_USER || ''
  const pass = process.env.SMTP_PASS || ''
  if (!host || !user || !pass) {
    return { ok: false, error: 'smtp_not_configured' }
  }
  const transporter = nodemailer.createTransport({
    host,
    port,
    secure: port === 465,
    auth: { user, pass }
  })
  try {
    const info = await transporter.sendMail({ from: user, to, subject, html })
    return { ok: true, id: info.messageId }
  } catch (e: any) {
    return { ok: false, error: String(e?.message || e) }
  }
}

