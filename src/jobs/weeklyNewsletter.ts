import { logger } from '../utils/logger.js'
import { listSources } from '../modules/sources/index.js'
import { transcribe } from '../modules/transcription/index.js'
import { summarizeTranscript, translateTitle } from '../modules/summarization/index.js'
import { selectTop, ContentItem } from '../modules/content/index.js'
import { listActive } from '../modules/subscribers/index.js'
import { distribute } from '../modules/distribution/index.js'
import { buildNewsletterHtml } from '../utils/newsletterTemplate.js'
import { fetchRssItems } from '../modules/rss/index.js'
import { insertContent, existsByOriginalUrl } from '../repository/contents.js'
import { upsertSourceByUrl } from '../repository/sources.js'

export async function runWeeklyNewsletter() {
  logger.info('Weekly pipeline starting')
  let sources = await listSources()
  if (!sources.length) {
    const envFeeds = (process.env.RSS_FEEDS || '').split(',').map(s => s.trim()).filter(Boolean)
    for (const u of envFeeds) {
      await upsertSourceByUrl('RSS Source', u, 'rss', 3)
    }
    if (envFeeds.length) {
      sources = await listSources()
    }
    if (!sources.length && envFeeds.length) {
      sources = envFeeds.map((u, idx) => ({
        id: `env-${idx}-${Date.now()}`,
        name: 'RSS Source',
        url: u,
        type: 'rss',
        active: true,
        maxItemsPerRun: 3,
        createdAt: new Date()
      })) as any
    }
  }
  const workSources = sources

  const collected: ContentItem[] = []
  const forceRecent = process.env.FORCE_RECENT === '1'

  for (const s of workSources) {
    if (!s.active) continue
    let items: { title: string; url: string; snippet?: string }[] = []
    if (s.type === 'rss') {
      const rss = await fetchRssItems(s.url, s.maxItemsPerRun || 3)
      items = rss.map(r => ({ title: r.title, url: r.link, snippet: r.contentSnippet }))
    } else {
      items = [{ title: `${s.name} 本周条目`, url: s.url }]
    }

    for (const it of items) {
      if (!forceRecent && await existsByOriginalUrl(it.url)) continue
      const tr = await transcribe(it.url)
      const text = tr.text || it.snippet || `内容：${it.title}`
      const sum = await summarizeTranscript(text)
      const zhTitle = await translateTitle(it.title)
      const content: ContentItem = {
        id: crypto.randomUUID(),
        sourceId: s.id,
        title: zhTitle,
        originalUrl: it.url,
        transcript: text.slice(0, 15000),
        summary: sum.summary || '',
        keyPoints: sum.keyPoints || [],
        qualityScore: Math.max(0, Math.min(1, Number(sum.qualityScore ?? 0.6))),
        processedAt: new Date(),
        status: 'approved'
      }
      collected.push(content)
      await insertContent(content as any)
    }
  }

  const top = selectTop(collected, 10)
  logger.info({ total: collected.length, selected: top.length }, 'Content selected')

  const subscribers = await listActive()
  const targets = subscribers.length ? subscribers : []

  if (!targets.length) {
    logger.warn('No active subscribers; skipping distribution')
    logger.info('Weekly pipeline done')
    return
  }

  for (const sub of targets) {
    const maxItems = sub.preferences?.maxItemsPerNewsletter ?? 10
    const chosen = top.slice(0, maxItems)
    const html = buildNewsletterHtml(chosen)
    const address = sub.identifier
    const res = await distribute(
      { title: '每周Newsletter', html },
      { channel: sub.channelType, address }
    )
    if (res.ok) {
      logger.info({ sub: sub.identifier, channel: sub.channelType }, 'Sent')
    } else {
      logger.error({ sub: sub.identifier, channel: sub.channelType, error: res.error }, 'Send failed')
    }
  }
  logger.info('Weekly pipeline done')
}
