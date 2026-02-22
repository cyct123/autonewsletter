export type UUID = string

export type SourceType = 'rss' | 'youtube' | 'podcast'

export interface Source {
  id: UUID
  name: string
  url: string
  type: SourceType
  active: boolean
  maxItemsPerRun: number
  createdAt: Date
}

export interface Content {
  id: UUID
  sourceId: UUID
  title: string
  originalUrl: string
  transcript: string
  summary: string
  keyPoints: string[]
  qualityScore: number
  processedAt: Date
  status: 'pending' | 'approved' | 'rejected' | 'sent'
}

export type ChannelType = 'wechat' | 'email' | 'lark' | 'pushplus'

export interface Subscriber {
  id: UUID
  channelType: ChannelType
  identifier: string
  name: string
  preferences: {
    maxItemsPerNewsletter: number
    language: 'zh' | 'en'
  }
  active: boolean
  subscribedAt: Date
}

export interface SendLog {
  id: UUID
  contentId: UUID
  subscriberId: UUID
  channelType: ChannelType
  status: 'success' | 'failed' | 'partial'
  errorMessage?: string
  sentAt: Date
}
