import { expect, test } from '@playwright/test'

test('I-0 registration, dashboard, logout and login', async ({ page }) => {
  await page.goto('/start')
  await expect(page.getByRole('heading', { name: 'Цифровая рабочая среда агрария' })).toBeVisible()
  await page.getByRole('link', { name: 'Зарегистрироваться' }).click()

  await page.getByLabel('Телефон').fill('+79005550101')
  await page.getByRole('button', { name: 'Получить код' }).click()
  await expect(page.getByText('Dev OTP: 000000')).toBeVisible()
  await page.getByLabel('Код из SMS').fill('000000')
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
  await expect(page.getByRole('heading', { name: 'Цифровая рабочая среда агрария' })).toBeVisible()
  await page.getByRole('link', { name: 'Войти' }).click()
  await page.getByLabel('Телефон').fill('+79005550101')
  await page.getByRole('button', { name: 'Получить код' }).click()
  await page.getByLabel('Код из SMS').fill('000000')
  await page.getByRole('button', { name: 'Войти' }).click()
  await expect(page.getByRole('heading', { name: 'Анна Тест' })).toBeVisible()
})
