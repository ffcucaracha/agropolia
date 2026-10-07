import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  use: {
    baseURL: 'http://localhost:5173',
    ...devices['Pixel 7'],
  },
  retries: 1,
  reporter: 'line',
})
