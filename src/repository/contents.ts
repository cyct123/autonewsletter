import { getDb } from '../config/database.js'
import type { Content } from '../types/models.js'

export async function existsByOriginalUrl(url: string): Promise<boolean> {
  if (!process.env.DATABASE_URL) return false
  const db = getDb()
  const res = await db.query(`SELECT 1 FROM contents WHERE original_url=$1 LIMIT 1`, [url])
  return (res.rowCount ?? 0) > 0
}

export async function insertContent(c: Content): Promise<void> {
  if (!process.env.DATABASE_URL) return
  const db = getDb()
  await db.query(
    `INSERT INTO contents (id, source_id, title, original_url, transcript, summary, key_points, quality_score, processed_at, status)
     VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)`,
    [
      c.id,
      c.sourceId,
      c.title,
      c.originalUrl,
      c.transcript,
      c.summary,
      c.keyPoints,
      c.qualityScore,
      c.processedAt,
      c.status
    ]
  )
}
