import { getDb } from '../config/database.js'
import type { Source } from '../types/models.js'

export async function listSourcesRepo(): Promise<Source[]> {
  if (!process.env.DATABASE_URL) return []
  const db = getDb()
  const res = await db.query(`SELECT id, name, url, type, active, max_items_per_run, created_at FROM sources WHERE active = true ORDER BY created_at DESC`)
  return res.rows.map((r: any) => ({
    id: r.id,
    name: r.name,
    url: r.url,
    type: r.type,
    active: r.active,
    maxItemsPerRun: Number(r.max_items_per_run ?? 3),
    createdAt: new Date(r.created_at)
  }))
}

export async function upsertSourceByUrl(name: string, url: string, type: 'rss' | 'youtube' | 'podcast', maxItemsPerRun = 3) {
  if (!process.env.DATABASE_URL) return
  const db = getDb()
  await db.query(
    `INSERT INTO sources (name, url, type, max_items_per_run, active)
     VALUES ($1,$2,$3,$4,true)
     ON CONFLICT (url) DO UPDATE SET name=EXCLUDED.name, type=EXCLUDED.type, max_items_per_run=EXCLUDED.max_items_per_run, active=true`,
    [name, url, type, maxItemsPerRun]
  )
}
