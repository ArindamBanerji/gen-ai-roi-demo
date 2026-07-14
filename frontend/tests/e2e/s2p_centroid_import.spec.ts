import { expect, test } from '@playwright/test'

const s2pApi = process.env.S2P_API_URL || 'http://127.0.0.1:8002'

test.describe.configure({ timeout: 90_000 })

function validCentroids(value = 0.5) {
  return Array.from({ length: 5 }, () =>
    Array.from({ length: 5 }, () =>
      Array.from({ length: 7 }, () => value),
    ),
  )
}

test.describe('S2P centroid import rejection smoke', () => {
  test('missing centroids returns 400', async ({ request }) => {
    const response = await request.post(`${s2pApi}/api/s2p/explorer/import/centroids`, {
      data: {},
    })

    expect(response.status()).toBe(400)
  })

  test('wrong shape returns 400', async ({ request }) => {
    const response = await request.post(`${s2pApi}/api/s2p/explorer/import/centroids`, {
      data: { centroids: [[[0.5]]] },
    })

    expect(response.status()).toBe(400)
  })

  test('out-of-range value returns 400', async ({ request }) => {
    const centroids = validCentroids()
    centroids[0][0][0] = 1.5
    const response = await request.post(`${s2pApi}/api/s2p/explorer/import/centroids`, {
      data: { centroids },
    })

    expect(response.status()).toBe(400)
  })
})
