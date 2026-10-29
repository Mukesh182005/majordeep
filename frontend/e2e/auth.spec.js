import { test, expect } from '@playwright/test'
import { uniqueEmail, watchPage } from './helpers.js'

const PASSWORD = 'e2e-Password-123'

test('register, sign out, sign in, wrong password', async ({ page, context }) => {
  const watch = watchPage(page)
  const email = uniqueEmail()

  await page.goto('/login')
  await page.getByRole('button', { name: /create one/i }).click()
  await page.locator('#full_name').fill('E2E Tester')
  await page.locator('#email').fill(email)
  await page.locator('#password').fill(PASSWORD)
  await page.getByRole('button', { name: /create account/i }).click()
  await expect(page.getByRole('button', { name: /sign out/i })).toBeVisible()

  // The session is an httpOnly cookie; no token in localStorage.
  const cookies = await context.cookies()
  const session = cookies.find((c) => c.httpOnly)
  expect(session, `cookies: ${cookies.map((c) => c.name).join(', ')}`).toBeTruthy()
  const stored = await page.evaluate(() => Object.keys(localStorage).filter((k) => /token/i.test(k)))
  expect(stored).toEqual([])
  const me = await page.request.get('/api/auth/me')
  expect(me.ok()).toBeTruthy()
  expect((await me.json()).email).toBe(email)

  await page.getByRole('button', { name: /sign out/i }).click()
  await expect(page.getByRole('link', { name: /sign in/i }).first()).toBeVisible()
  expect((await page.request.get('/api/auth/me')).status()).toBe(401)

  await page.goto('/login')
  await page.locator('#email').fill(email)
  await page.locator('#password').fill('wrong-password-000')
  await page.getByRole('button', { name: /^sign in/i }).click()
  await expect(page.getByText(/invalid|incorrect|wrong/i).first()).toBeVisible()

  await page.locator('#password').fill(PASSWORD)
  await page.getByRole('button', { name: /^sign in/i }).click()
  await expect(page.getByRole('button', { name: /sign out/i })).toBeVisible()
  // A failed sign-in answers 401, which the browser logs; anything else is a fault.
  watch.check(['401'])
})
