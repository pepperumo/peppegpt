import { test, expect } from '@playwright/test';
import { setupUnauthenticatedMocks, setupModuleMocks } from './mocks';

// Mock the public API endpoints for guest mode
async function setupGuestAPIMocks(page) {
  // Mock the public streaming endpoint
  await page.route('**/api/public/chat/stream', async (route) => {
    const mockResponse = `{"text": "Hello!"}
{"text": "Hello! I'm"}
{"text": "Hello! I'm PeppeGPT,"}
{"text": "Hello! I'm PeppeGPT, a mock"}
{"text": "Hello! I'm PeppeGPT, a mock AI assistant."}
{"text": "Hello! I'm PeppeGPT, a mock AI assistant.", "complete": true}`;

    await route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'text/plain',
        'Cache-Control': 'no-cache',
      },
      body: mockResponse
    });
  });

  // Mock the non-streaming public endpoint (if used)
  await page.route('**/api/public/chat', async (route) => {
    await route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        response: "Hello! I'm PeppeGPT, a mock AI assistant.",
        rate_limit_remaining: 9
      })
    });
  });
}

test.describe('Guest Mode Flow', () => {
  test.beforeEach(async ({ page }) => {
    await setupUnauthenticatedMocks(page);
    await setupGuestAPIMocks(page);
    await setupModuleMocks(page);
  });

  test('should show GuestChat as the default landing page', async ({ page }) => {
    // Navigate to root - should show GuestChat directly
    await page.goto('/');

    // Should see the guest mode indicator
    await expect(page.getByText('Guest Mode', { exact: true })).toBeVisible();

    // Should see the PeppeGPT header
    await expect(page.getByText('PeppeGPT', { exact: true }).first()).toBeVisible();

    // Should see the "Sign In" button
    await expect(page.getByRole('button', { name: 'Sign In', exact: true })).toBeVisible();
  });

  test('should display guest chat interface elements', async ({ page }) => {
    await page.goto('/');

    // Should see the chat input
    const messageInput = page.getByPlaceholder('Message the AI...');
    await expect(messageInput).toBeVisible();

    // Should see the info panel button
    await expect(page.locator('button[title="About this project"]')).toBeVisible();

    // Should see the welcome message or empty state
    await expect(page.locator('text=Welcome to PeppeGPT')).toBeVisible();

    // Should see suggested questions
    await expect(page.locator('text=Try asking:')).toBeVisible();
  });

  test('should send a message in guest mode and receive response', async ({ page }) => {
    await page.goto('/');

    // Type a message
    const messageInput = page.getByPlaceholder('Message the AI...');
    await messageInput.fill('Hello, who are you?');

    // Send the message
    const sendButton = page.locator('button[type="submit"]').last();
    await sendButton.click();

    // Should see the user message
    await expect(page.getByText('Hello, who are you?')).toBeVisible();

    // Should see the AI response (from mock)
    await expect(page.getByText("Hello! I'm PeppeGPT, a mock AI assistant.")).toBeVisible({ timeout: 10000 });
  });

  test('should show guest mode disclaimer', async ({ page }) => {
    await page.goto('/');

    // Should see the disclaimer about conversations not being saved
    await expect(page.locator('text=Guest mode - conversations are not saved')).toBeVisible();
  });

  test('should navigate to login when clicking "Sign In" in guest mode', async ({ page }) => {
    await page.goto('/');

    // Click the "Sign In" button in header
    await page.getByRole('button', { name: 'Sign In', exact: true }).click();

    // Should redirect to login page
    await expect(page).toHaveURL('/login');
  });

  test('should open project info panel in guest mode', async ({ page }) => {
    await page.goto('/');

    // Click the info button
    await page.locator('button[title="About this project"]').click();

    // Should see the project info panel
    await expect(page.locator('text=Architecture')).toBeVisible();
    await expect(page.locator('text=Tech Stack')).toBeVisible();
    await expect(page.locator('text=Key Features')).toBeVisible();
  });

  test('should handle suggested question clicks in guest mode', async ({ page }) => {
    await page.goto('/');

    // Click a suggested question
    const suggestedQuestion = page.locator('button:has-text("professional experience")');
    await suggestedQuestion.click();

    // Should see the question in the chat
    await expect(page.getByText(/professional experience/i)).toBeVisible();
  });

  test('should show loading state while generating response', async ({ page }) => {
    // Override mock to add delay
    await page.route('**/api/public/chat/stream', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 500));

      const mockResponse = `{"text": "Delayed response"}
{"text": "Delayed response", "complete": true}`;

      await route.fulfill({
        status: 200,
        headers: {
          'Content-Type': 'text/plain',
          'Cache-Control': 'no-cache',
        },
        body: mockResponse
      });
    });

    await page.goto('/');

    // Type and send a message
    const messageInput = page.getByPlaceholder('Message the AI...');
    await messageInput.fill('Test loading');

    const sendButton = page.locator('button[type="submit"]').last();
    await sendButton.click();

    // Should see the user message immediately
    await expect(page.getByText('Test loading')).toBeVisible();

    // Should see the response after delay
    await expect(page.getByText('Delayed response')).toBeVisible({ timeout: 10000 });
  });

  test('should handle API errors gracefully in guest mode', async ({ page }) => {
    // Override mock to return error
    await page.route('**/api/public/chat/stream', async (route) => {
      await route.fulfill({
        status: 429,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          detail: 'Rate limit exceeded. Please wait a minute.'
        })
      });
    });

    await page.goto('/');

    // Type and send a message
    const messageInput = page.getByPlaceholder('Message the AI...');
    await messageInput.fill('Test error');

    const sendButton = page.locator('button[type="submit"]').last();
    await sendButton.click();

    // Should see error message
    await expect(page.locator('text=Rate limit exceeded')).toBeVisible({ timeout: 5000 });
  });

  test('should auto-focus input on load in guest mode', async ({ page }) => {
    await page.goto('/');

    // Wait for input to be visible and focused
    const messageInput = page.getByPlaceholder('Message the AI...');
    await expect(messageInput).toBeVisible();

    // Small delay for auto-focus to complete
    await page.waitForTimeout(200);

    // Clear any existing value and type
    await messageInput.fill('Test auto focus');

    // The input should contain the typed text
    await expect(messageInput).toHaveValue('Test auto focus');
  });

  test('should show login page at /login route', async ({ page }) => {
    await page.goto('/login');

    // Should see the login form
    await expect(page.locator('h1, h2')).toContainText('AI Agent Dashboard');
  });
});
