import { expect, test } from '@playwright/test'

const s2pApi = process.env.S2P_API_URL || 'http://127.0.0.1:8002'

test.describe('S2P preview observation wiring', () => {
  test.describe.configure({ timeout: 90_000 })

  test('preview queue does not change conservation decision counts', async ({ request }) => {
    const before = await request.get(`${s2pApi}/api/conservation/status`)
    expect(before.status()).toBe(200)
    const beforeData = await before.json()

    const queue = await request.get(`${s2pApi}/api/s2p/preview/queue`)
    expect(queue.status()).toBe(200)
    const queueData = await queue.json()
    expect(queueData.showing).toBeGreaterThan(0)
    expect(Array.isArray(queueData.invoices)).toBe(true)
    expect(Array.isArray(queueData.exceptions)).toBe(true)

    const after = await request.get(`${s2pApi}/api/conservation/status`)
    expect(after.status()).toBe(200)
    const afterData = await after.json()

    expect(afterData.total_decisions).toBe(beforeData.total_decisions)
    expect(afterData.verified_count).toBe(beforeData.verified_count)
    expect(afterData.correct_count).toBe(beforeData.correct_count)
  })
})
