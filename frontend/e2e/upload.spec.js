import { test, expect } from '@playwright/test'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { expectImagesLoaded, fixture, uniqueEmail, uploadAndWait, watchPage } from './helpers.js'

test.describe('rejected uploads', () => {
  test('a text file renamed to .jpg is refused with a message', async ({ page }) => {
    await page.goto('/analyse')
    await page.locator('input[type="file"]').setInputFiles(fixture('not_image.jpg'))
    const submit = page.locator('#btn-start-analysis')
    if (await submit.isEnabled()) await submit.click()
    await expect(page.getByText(/not accepted|not a valid|unsupported|could not|does not match|corrupt/i).first()).toBeVisible()
    await expect(page).toHaveURL(/\/analyse/)
  })

  test('an unsupported file type is refused', async ({ page }) => {
    const exe = path.join(os.tmpdir(), `e2e-${Date.now()}.exe`)
    fs.writeFileSync(exe, Buffer.from('MZ\x90\x00not a program'))
    await page.goto('/analyse')
    await page.locator('input[type="file"]').setInputFiles(exe)
    const submit = page.locator('#btn-start-analysis')
    if (await submit.isEnabled()) await submit.click()
    await expect(page.getByText(/not accepted|unsupported|not supported|allowed/i).first()).toBeVisible()
    fs.unlinkSync(exe)
  })

  test('a file above the upload limit is refused', async ({ page, request }) => {
    const { max_upload_mb: maxMb } = await (await request.get('/api/upload/limits')).json()
    const big = path.join(os.tmpdir(), `e2e-big-${Date.now()}.jpg`)
    const jpeg = fs.readFileSync(fixture('real.jpg'))
    fs.writeFileSync(big, Buffer.concat([jpeg, Buffer.alloc((maxMb + 1) * 1024 * 1024)]))
    await page.goto('/analyse')
    await page.locator('input[type="file"]').setInputFiles(big)
    const submit = page.locator('#btn-start-analysis')
    if (await submit.isEnabled()) await submit.click()
    await expect(page.getByText(/too large|exceeds|limit|MB/i).first()).toBeVisible()
    fs.unlinkSync(big)
  })
})

test.describe('analysis @slow', () => {
  test('guest image upload: verdict, scores, evidence images, PDF report', async ({ page }) => {
    const watch = watchPage(page)
    const jobId = await uploadAndWait(page, fixture('ai.jpg'))
    await expectImagesLoaded(page)

    const result = await (await page.request.get(`/api/jobs/${jobId}/result`)).json()
    expect(['AUTHENTIC', 'MANIPULATED', 'INCONCLUSIVE']).toContain(result.verdict)
    expect(Object.keys(result.evidence.scene_model_scores).length).toBeGreaterThanOrEqual(2)
    expect(JSON.stringify(result.evidence)).not.toMatch(/[A-Z]:\\\\Users/) // no local file paths

    const links = await (await page.request.post(`/api/jobs/${jobId}/links`)).json()
    const pdf = await page.request.get(links.report_url)
    expect(pdf.ok()).toBeTruthy()
    expect((await pdf.body()).subarray(0, 5).toString()).toBe('%PDF-')

    const report = await (await page.request.post(`/api/jobs/${jobId}/report`)).json()
    const verify = await page.request.get(`/api/reports/${report.report_reference}/verify`)
    expect(verify.ok()).toBeTruthy()
    watch.check()
  })

  test('real photo upload reaches a verdict', async ({ page }) => {
    await uploadAndWait(page, fixture('real.jpg'))
    await expectImagesLoaded(page)
  })

  test('audio upload: pellav2 score and windows', async ({ page }) => {
    const jobId = await uploadAndWait(page, fixture('speech.wav'))
    await expectImagesLoaded(page)
    const result = await (await page.request.get(`/api/jobs/${jobId}/result`)).json()
    const pellav2 = result.evidence.models_output?.pellav2
    expect(pellav2, 'pellav2 ran').toBeTruthy()
    expect(pellav2.n_windows).toBeGreaterThanOrEqual(1)
    expect(result.evidence.notes.join(' ')).toMatch(/pellav2|ASVspoof/)
  })

  test('video upload: timeline, scene score over several frames', async ({ page }) => {
    const jobId = await uploadAndWait(page, fixture('clip.mp4'))
    await expectImagesLoaded(page)
    const result = await (await page.request.get(`/api/jobs/${jobId}/result`)).json()
    expect(result.evidence.frames_analysed).toBeGreaterThan(0)
    expect(result.evidence.scene_frame_scores.length).toBeGreaterThan(1)
    expect(result.evidence).toHaveProperty('gend_face_mean') // null when no face is found (synthetic clip)
  })

  test('signed-in history lists and deletes a job, and its files are gone', async ({ page }) => {
    await page.goto('/login')
    await page.getByRole('button', { name: /create one/i }).click()
    await page.locator('#email').fill(uniqueEmail())
    await page.locator('#password').fill('e2e-Password-123')
    await page.getByRole('button', { name: /create account/i }).click()
    await expect(page.getByRole('button', { name: /sign out/i })).toBeVisible()

    const jobId = await uploadAndWait(page, fixture('real.jpg'))
    const result = await (await page.request.get(`/api/jobs/${jobId}/result`)).json()
    const evidenceUrls = Object.entries(result.evidence).filter(([k, v]) => k.endsWith('_url') && v).map(([, v]) => v)
    expect(evidenceUrls.length).toBeGreaterThan(0)

    await page.goto('/history')
    const del = page.getByRole('button', { name: new RegExp(`Delete ${result.original_filename}`) }).first()
    await expect(del).toBeVisible()
    page.once('dialog', (d) => d.accept())
    await del.click()
    await expect(del).toBeHidden()
    expect((await page.request.get(`/api/jobs/${jobId}/result`)).status()).toBe(404)
    for (const url of evidenceUrls) expect((await page.request.get(url)).status()).toBe(404)
  })
})
