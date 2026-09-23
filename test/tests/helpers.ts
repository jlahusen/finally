import { expect, type Page } from '@playwright/test';

export const DEFAULT_TICKERS = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META', 'JPM', 'V', 'NFLX'];

/** Parse a formatted money string like "$10,000.00" or "-$1.23" into a number. */
export function money(text: string): number {
  return Number(text.replace(/[^0-9.-]/g, ''));
}

/** Open the app and wait until the SSE stream is connected. */
export async function openApp(page: Page) {
  await page.goto('/');
  await expect(page.getByTestId('connection-status')).toHaveAttribute('data-state', 'connected');
}

/** Read the header cash balance as a number. */
export async function headerCash(page: Page): Promise<number> {
  return money(await page.getByTestId('header-cash').innerText());
}

/** Submit a market order through the trade bar. */
export async function trade(page: Page, ticker: string, quantity: number, side: 'buy' | 'sell') {
  await page.getByTestId('trade-ticker').fill(ticker);
  await page.getByTestId('trade-quantity').fill(String(quantity));
  await page.getByTestId(`trade-${side}`).click();
}
