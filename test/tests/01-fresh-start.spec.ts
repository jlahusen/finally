import { test, expect } from '@playwright/test';
import { DEFAULT_TICKERS, openApp } from './helpers';

test('fresh start shows default watchlist, $10k and streaming prices', async ({ page }) => {
  await openApp(page);

  for (const ticker of DEFAULT_TICKERS) {
    await expect(page.getByTestId(`watchlist-row-${ticker}`)).toBeVisible();
  }
  await expect(page.locator('[data-testid^="watchlist-row-"]')).toHaveCount(10);

  await expect(page.getByTestId('header-cash')).toHaveText('$10,000.00');
  await expect(page.getByTestId('header-total-value')).toHaveText('$10,000.00');

  const price = page.getByTestId('watchlist-price-AAPL');
  await expect(price).toHaveText(/\d+\.\d{2}/);
  const first = await price.innerText();
  await expect(price).not.toHaveText(first);
});
