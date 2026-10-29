import { expect } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

export const FIXTURES = path.join(path.dirname(fileURLToPath(import.meta.url)), 'fixtures')
export const fixture = (name) => path.join(FIXTURES, name)

/** Collects console errors and failed same-origin requests; call check() at the end of a test. */
export function watchPage(page) {
  const problems = []
  page.on('console', (msg) => {
    if (msg.type() !== 'error') return
    // A guest's session check (GET /api/auth/me) answers 401 by design; Chrome logs it.
    if (msg.location().url.endsWith('/api/auth/me')) return
    problems.push(`console: ${msg.text()} (${msg.location().url})`)
  })
  page.on('pageerror', (err) => problems.push(`page error: ${err.message}`))
  page.on('response', (res) => {
    const url = new URL(res.url())
    if (url.origin === new URL(page.url() || res.url()).origin && res.status() === 404) {
      problems.push(`404: ${url.pathname}`)
    }
  })
  return {
    problems,
    check(allow = []) {
      const left = problems.filter((p) => !allow.some((a) => p.includes(a)))
      expect(left, left.join('\n')).toEqual([])
    },
  }
}

/** Upload a file on /analyse and wait for the result page to show a verdict. */
export async function uploadAndWait(page, file) {
  await page.goto('/analyse')
  await page.locator('input[type="file"]').setInputFiles(file)
  await page.locator('#btn-start-analysis').click()
  await page.waitForURL(/\/jobs\/[0-9a-f-]+$/, { timeout: 60 * 1000 })
  const jobId = page.url().split('/jobs/')[1]
  const verdict = page.getByText(/No manipulation detected|Likely manipulated|Likely AI-generated|Inconclusive/i).first()
  await expect(verdict).toBeVisible({ timeout: 9 * 60 * 1000 })
  return jobId
}

/** Every evidence image on the page has loaded with real pixels. */
export async function expectImagesLoaded(page) {
  await page.waitForLoadState('networkidle')
  const broken = await page.$$eval('img', (imgs) =>
    imgs.filter((i) => i.complete && i.naturalWidth === 0 && i.getAttribute('src')).map((i) => i.getAttribute('src')))
  expect(broken, `broken images: ${broken.join(', ')}`).toEqual([])
}

export function uniqueEmail() {
  return `e2e-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`
}
