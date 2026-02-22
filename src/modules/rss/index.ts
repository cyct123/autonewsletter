import Parser from 'rss-parser'

export interface RssItem {
  title: string
  link: string
  contentSnippet?: string
}

const parser = new Parser()

export async function fetchRssItems(url: string, limit: number): Promise<RssItem[]> {
  try {
    const feed = await parser.parseURL(url)
    const items: RssItem[] = []
    for (const it of feed.items || []) {
      if (!it.link || !it.title) continue
      items.push({
        title: it.title,
        link: it.link,
        contentSnippet: it.contentSnippet || it.content || it.summary || ''
      })
      if (items.length >= limit) break
    }
    return items
  } catch {
    return []
  }
}
