export function assertString(input: unknown, fallback: string = ''): string {
  if (typeof input === 'string') return input
  return fallback
}

export function clamp01(n: number) {
  if (n < 0) return 0
  if (n > 1) return 1
  return n
}

