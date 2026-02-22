export type Channel = 'wechat' | 'email' | 'lark' | 'pushplus'

export interface Subscriber {
  id: string
  channelType: Channel
  identifier: string
  name: string
  preferences: {
    maxItemsPerNewsletter: number
    language: 'zh' | 'en'
  }
  active: boolean
  subscribedAt: Date
}

export async function listActive(): Promise<Subscriber[]> {
  const out: Subscriber[] = []
  const envMany = process.env.WECHAT_WEBHOOK_URLS || ''
  const envOne = process.env.WECHAT_WEBHOOK_URL || ''
  const urls = envMany
    ? envMany.split(',').map(s => s.trim()).filter(Boolean)
    : (envOne ? [envOne] : [])
  for (const u of urls) {
    out.push({
      id: crypto.randomUUID(),
      channelType: 'wechat',
      identifier: u,
      name: 'WeChat Group',
      preferences: { maxItemsPerNewsletter: 10, language: 'zh' },
      active: true,
      subscribedAt: new Date()
    })
  }
  const tokensEnv = process.env.PUSHPLUS_TOKENS || ''
  const tokens = tokensEnv ? tokensEnv.split(',').map(s => s.trim()).filter(Boolean) : []
  for (const t of tokens) {
    out.push({
      id: crypto.randomUUID(),
      channelType: 'pushplus',
      identifier: t,
      name: 'WeChat Personal',
      preferences: { maxItemsPerNewsletter: 10, language: 'zh' },
      active: true,
      subscribedAt: new Date()
    })
  }
  return out
}
