import { test, expect } from '@playwright/test'
import { watchPage } from './helpers.js'

const PAGES = [
  ['/', /DeepSentinel|deepfake/i],
  ['/how-it-works', /how/i],
  ['/privacy', /privacy/i],
  ['/analyse', /analy/i],
  ['/login', /sign in|welcome back/i],
]

for (const [route, text] of PAGES) {
  test(`page ${route} loads without errors`, async ({ page }) => {
    const watch = watchPage(page)
    await page.goto(route)
    await expect(page.locator('body')).toContainText(text)
    await page.waitForLoadState('networkidle')
    watch.check()
  })
}

test('history redirects a guest to sign in', async ({ page }) => {
  await page.goto('/history')
  await expect(page).toHaveURL(/\/login/)
})

test('upload limits come from the API', async ({ request }) => {
  const res = await request.get('/api/upload/limits')
  expect(res.ok()).toBeTruthy()
  const limits = await res.json()
  expect(limits.enabled_media_types).toEqual(expect.arrayContaining(['image', 'audio', 'video']))
})

test.describe('mobile 390x844', () => {
  test.use({ viewport: { width: 390, height: 844 } })
  for (const route of ['/', '/analyse', '/privacy', '/how-it-works', '/login']) {
    test(`no horizontal scroll on ${route}`, async ({ page }) => {
      await page.goto(route)
      await page.waitForLoadState('networkidle')
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
      expect(overflow).toBeLessThanOrEqual(1)
    })
  }
})

test('result and how-it-works pages make no unbacked claims', async ({ page }) => {
  for (const route of ['/', '/how-it-works', '/privacy']) {
    await page.goto(route)
    const text = await page.locator('body').innerText()
    for (const claim of [/WavLM/i, /Whisper/i, /SWGDE/, /Daubert/, /court[- ]ready/i, /ISO(\/IEC)? ?2703[78]/, /Zero Bias/i]) {
      expect(text, `${route} mentions ${claim}`).not.toMatch(claim)
    }
  }
})
