import { test, expect } from '@playwright/test';
import { openApp, trade } from './helpers';

/** Colour of each heatmap cell (its own fill/background, or its first rect's fill), keyed by data-pnl. */
async function heatmapColours(page: import('@playwright/test').Page) {
  return page.locator('[data-testid^="heatmap-cell-"]').evaluateAll((cells) =>
    cells.map((cell) => {
      const target = cell.tagName.toLowerCase() === 'g' ? cell.querySelector('rect') ?? cell : cell;
      const style = getComputedStyle(target);
      const colour = target instanceof SVGElement ? style.fill : style.backgroundColor;
      return { pnl: cell.getAttribute('data-pnl'), colour };
    }),
  );
}

test('heatmap colours match P&L and P&L chart has data points', async ({ page, request }) => {
  await openApp(page);
  await trade(page, 'META', 1, 'buy');
  await expect(page.getByTestId('position-row-META')).toBeVisible();
  await trade(page, 'TSLA', 1, 'buy');
  await expect(page.getByTestId('position-row-TSLA')).toBeVisible();

  for (const ticker of ['META', 'TSLA']) {
    await expect(page.getByTestId(`heatmap-cell-${ticker}`)).toHaveAttribute('data-pnl', /^(up|down|flat)$/);
  }
  const cells = await heatmapColours(page);
  const upColours = cells.filter((c) => c.pnl === 'up').map((c) => c.colour);
  const downColours = cells.filter((c) => c.pnl === 'down').map((c) => c.colour);
  for (const colour of upColours) expect(downColours).not.toContain(colour);

  const history = await (await request.get('/api/portfolio/history')).json();
  expect(history.length).toBeGreaterThanOrEqual(2);
  await expect(page.getByTestId('pnl-chart')).toHaveAttribute('data-points', /^([2-9]|\d{2,})$/);
  await expect(page.getByTestId('pnl-chart').locator('svg path').first()).toBeAttached();
});
