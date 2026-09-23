import { test, expect } from '@playwright/test';
import { headerCash, openApp, trade } from './helpers';

test('buying shares lowers cash and adds a position', async ({ page }) => {
  await openApp(page);
  const cashBefore = await headerCash(page);

  await trade(page, 'NVDA', 2, 'buy');

  await expect(page.getByTestId('position-row-NVDA')).toBeVisible();
  await expect.poll(() => headerCash(page)).toBeLessThan(cashBefore);
  await expect(page.getByTestId('heatmap-cell-NVDA')).toBeVisible();
});
