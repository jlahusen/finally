import { test, expect } from '@playwright/test';
import { headerCash, openApp, trade } from './helpers';

test('selling part of a position raises cash and keeps the row', async ({ page, request }) => {
  await openApp(page);
  await trade(page, 'JPM', 5, 'buy');
  await expect(page.getByTestId('position-row-JPM')).toBeVisible();
  const cashBefore = await headerCash(page);

  await trade(page, 'JPM', 2, 'sell');

  await expect.poll(() => headerCash(page)).toBeGreaterThan(cashBefore);
  await expect(page.getByTestId('position-row-JPM')).toBeVisible();
  const portfolio = await (await request.get('/api/portfolio')).json();
  const jpm = portfolio.positions.find((p: { ticker: string }) => p.ticker === 'JPM');
  expect(jpm.quantity).toBe(3);
});

test('selling the full quantity removes the position row', async ({ page }) => {
  await openApp(page);
  await trade(page, 'V', 3, 'buy');
  await expect(page.getByTestId('position-row-V')).toBeVisible();

  await trade(page, 'V', 3, 'sell');

  await expect(page.getByTestId('position-row-V')).toHaveCount(0);
  await expect(page.getByTestId('heatmap-cell-V')).toHaveCount(0);
});

test('selling more than held shows an error', async ({ page }) => {
  await openApp(page);

  await trade(page, 'NFLX', 1, 'sell');

  await expect(page.getByTestId('trade-error')).toContainText('insufficient shares');
});
