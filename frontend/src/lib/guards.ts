/**
 * Type guards for API response data.
 *
 * These guards are the frontend's defense against unexpected API data.
 * Every .map(), .filter(), .length call on API data MUST go through these.
 *
 * If a guard fires (logs a warning), the root cause is upstream:
 * fix AGEClient._normalize_value or the backend endpoint, not the guard.
 */

export function ensureArray<T>(value: unknown, fallback: T[] = []): T[] {
  if (Array.isArray(value)) return value
  if (value == null) return fallback
  console.warn('[guards] ensureArray: expected array, got', typeof value, value)
  // If it's a string that looks like JSON array, try parsing
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value)
      if (Array.isArray(parsed)) return parsed
    } catch { /* not JSON */ }
  }
  return fallback
}

export function ensureNumber(value: unknown, fallback: number = 0): number {
  if (typeof value === 'number' && !isNaN(value)) return value
  if (typeof value === 'string') {
    const parsed = parseFloat(value)
    if (!isNaN(parsed)) return parsed
  }
  if (value != null) {
    console.warn('[guards] ensureNumber: expected number, got', typeof value, value)
  }
  return fallback
}

export function ensureString(value: unknown, fallback: string = ''): string {
  if (typeof value === 'string') return value
  if (value == null) return fallback
  console.warn('[guards] ensureString: expected string, got', typeof value, value)
  return String(value)
}

export function ensureObject<T extends Record<string, unknown>>(
  value: unknown,
  fallback: T = {} as T
): T {
  if (value != null && typeof value === 'object' && !Array.isArray(value)) {
    return value as T
  }
  if (value != null) {
    console.warn('[guards] ensureObject: expected object, got', typeof value, value)
  }
  return fallback
}

export function safeKey(id: unknown, index: number): string {
  if (id != null && id !== '' && id !== 'None' && id !== 'null') {
    return String(id)
  }
  return `fallback-${index}`
}
