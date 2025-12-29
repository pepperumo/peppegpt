import { test, expect } from '@playwright/test';
import { setupUnauthenticatedMocks, setupAgentAPIMocks, setupModuleMocks } from './mocks';

// Skip in CI - auth mocking doesn't work with real Supabase credentials
test.skip(() => !!process.env.CI, 'E2E tests require real auth session');

test('basic test - page loads', async ({ page }) => {
  await setupUnauthenticatedMocks(page);
  await setupAgentAPIMocks(page);
  await setupModuleMocks(page);
  
  await page.goto('/');
  
  // Just verify the page loads
  await expect(page).toHaveTitle(/PeppeGPT/);
});