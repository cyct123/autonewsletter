export interface ContentItem {
  id: string
  sourceId: string
  title: string
  originalUrl: string
  transcript: string
  summary: string
  keyPoints: string[]
  qualityScore: number
  processedAt: Date
  status: 'pending' | 'approved' | 'rejected' | 'sent'
}

export function selectTop(items: ContentItem[], limit: number) {
  return items
    .filter((i) => i.status !== 'rejected')
    .sort((a, b) => b.qualityScore - a.qualityScore)
    .slice(0, limit)
}

export function needsReview(text: string, score: number) {
  const blockWords = ['政治', '暴力', '色情']
  const hit = blockWords.some((w) => text.includes(w))
  return hit && score > 0.8
}

