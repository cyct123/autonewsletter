export type SourceType = 'rss' | 'youtube' | 'podcast'

export interface Source {
  id: string
  name: string
  url: string
  type: SourceType
  active: boolean
  maxItemsPerRun: number
  createdAt: Date
}

export async function listSources(): Promise<Source[]> {
  const mod = await import('../../repository/sources.js')
  return mod.listSourcesRepo()
}

export async function addSource(_: Omit<Source, 'id' | 'createdAt'>) {
  return { ok: false }
}
