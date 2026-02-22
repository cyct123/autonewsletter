import { spawn } from 'node:child_process'

export async function transcribe(audioUrl: string): Promise<{ text: string }> {
  const proc = spawn('python3', ['src/services/whisper.py'])
  const payload = JSON.stringify({ audio_url: audioUrl })
  return new Promise((resolve) => {
    let out = ''
    proc.stdout.on('data', (d: Buffer) => (out += d.toString()))
    proc.stdin.write(payload)
    proc.stdin.end()
    proc.on('close', () => {
      try {
        const obj = JSON.parse(out || '{}')
        resolve({ text: String(obj.text || '') })
      } catch {
        resolve({ text: '' })
      }
    })
  })
}
