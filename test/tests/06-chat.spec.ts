import { test, expect } from '@playwright/test';
import { openApp } from './helpers';

async function sendChat(page: import('@playwright/test').Page, text: string) {
  await page.getByTestId('chat-input').fill(text);
  await page.getByTestId('chat-send').click();
}

test('mocked AI chat executes a trade and shows the notice inline', async ({ page }) => {
  await openApp(page);

  await sendChat(page, 'buy 2 AMZN');

  const reply = page.locator('[data-testid="chat-message"][data-role="assistant"]').last();
  await expect(reply).toContainText('Mock reply');
  const notice = page.getByTestId('chat-action').last();
  await expect(notice).toHaveAttribute('data-ok', 'true');
  await expect(notice).toContainText(/Bought 2 AMZN @ \$/);
  await expect(page.getByTestId('position-row-AMZN')).toBeVisible();
});

test('mocked AI chat shows a failed trade notice', async ({ page }) => {
  await openApp(page);

  await sendChat(page, 'sell 1000 GOOGL');

  const notice = page.getByTestId('chat-action').last();
  await expect(notice).toHaveAttribute('data-ok', 'false');
  await expect(notice).toContainText('insufficient shares');
});

test('chat history survives a page reload', async ({ page }) => {
  await openApp(page);
  const text = `hello from e2e ${Date.now()}`;

  await sendChat(page, text);
  await expect(page.locator('[data-testid="chat-message"][data-role="assistant"]').last()).toContainText('Mock reply');

  await page.reload();
  await expect(page.locator('[data-testid="chat-message"][data-role="user"]', { hasText: text })).toBeVisible();
});
