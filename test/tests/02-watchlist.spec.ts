import { test, expect } from '@playwright/test';
import { openApp } from './helpers';

test('add and remove a ticker from the watchlist', async ({ page }) => {
  await openApp(page);

  await page.getByTestId('watchlist-add-input').fill('PYPL');
  await page.getByTestId('watchlist-add-button').click();

  await expect(page.getByTestId('watchlist-row-PYPL')).toBeVisible();
  await expect(page.getByTestId('watchlist-price-PYPL')).toHaveText(/\d+\.\d{2}/);

  await page.getByTestId('watchlist-row-PYPL').hover();
  await page.getByTestId('watchlist-remove-PYPL').click();
  await expect(page.getByTestId('watchlist-row-PYPL')).toHaveCount(0);

  await page.reload();
  await expect(page.getByTestId('watchlist-row-AAPL')).toBeVisible();
  await expect(page.getByTestId('watchlist-row-PYPL')).toHaveCount(0);
});
