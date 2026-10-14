import { expect, test } from '@playwright/test'

test('I-0 email registration, dashboard, logout and login', async ({ page }) => {
  const email = 'i0-user@agropolia.local'

  await page.goto('/start')
  await expect(page.getByRole('heading', { name: 'Цифровая рабочая среда агрария' })).toBeVisible()
  await page.getByRole('link', { name: 'Зарегистрироваться' }).click()

  await page.getByLabel('Email').fill(email)
  await page.getByRole('button', { name: 'Получить код' }).click()
  const devOtpText = await page.locator('.dev-note').textContent()
  const code = devOtpText?.replace(/\D/g, '') ?? ''
  await page.getByLabel('Код из письма').fill(code)
  await page.getByRole('button', { name: 'Продолжить' }).click()

  await page.getByLabel('Имя').fill('Анна Тест')
  await page.getByLabel('Тип хозяйства').selectOption('KFH')
  await page.getByLabel('ИНН').fill('7707083893')
  await page.getByLabel('Название хозяйства').fill('КФХ Тест')
  await page.getByLabel('Согласен на обработку персональных данных').check()
  await page.getByRole('button', { name: 'Создать хозяйство' }).click()

  await expect(page.getByRole('heading', { name: 'Анна Тест' })).toBeVisible()
  await expect(page.getByText('КФХ Тест')).toBeVisible()
  await expect(page.getByText('7707083893')).toBeVisible()
  await expect(page.getByText('owner')).toBeVisible()

  await page.getByRole('button', { name: 'Выйти' }).click()
  await page.getByRole('link', { name: 'Войти' }).click()
  await page.getByLabel('Email').fill(email)
  await page.getByRole('button', { name: 'Получить код' }).click()
  const loginOtpText = await page.locator('.dev-note').textContent()
  const loginCode = loginOtpText?.replace(/\D/g, '') ?? ''
  await page.getByLabel('Код из письма').fill(loginCode)
  await page.getByRole('button', { name: 'Войти' }).click()
  await expect(page.getByRole('heading', { name: 'Анна Тест' })).toBeVisible()
})
