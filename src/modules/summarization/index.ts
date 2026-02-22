import { summarize, translateTitleToZh } from '../../services/openai.js'

export async function summarizeTranscript(text: string) {
  return summarize(text)
}

export async function translateTitle(title: string) {
  const ascii = (title.match(/[A-Za-z0-9\s]/g) || []).length
  const ratio = ascii / Math.max(1, title.length)
  if (ratio >= 0.6) {
    return translateTitleToZh(title)
  }
  return title
}
