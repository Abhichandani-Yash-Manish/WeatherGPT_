/* Every registered route loads, states its heading, and does it without a console error or a failed request.
   The route list is read from the surface registry so a new surface is covered the moment it is registered. */
import { expect, test } from '@playwright/test';
import { VIEWS } from '../../src/shell/views';

const ROUTES = VIEWS.map(view => view.id);

for (const route of ROUTES) {
  test('#' + route + ' loads with its heading and no failed request', async ({ page }) => {
    const failures: string[] = [];
    const consoleErrors: string[] = [];
    page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text().slice(0, 200)); });
    page.on('response', response => { if (response.status() >= 400) failures.push(response.status() + ' ' + response.url()); });

    await page.goto('/#/' + route, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('main')).toBeVisible({ timeout: 30_000 });

    const heading = page.locator('main h1').first();
    await expect(heading).toBeVisible({ timeout: 20_000 });
    await expect(heading).not.toBeEmpty();

    /* The page settles: a read in flight is allowed, a broken read is not. */
    await page.waitForTimeout(1500);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, 'horizontal overflow in px at ' + route).toBeLessThanOrEqual(1);
    expect(failures, 'failed requests on #' + route).toEqual([]);
    expect(consoleErrors, 'console errors on #' + route).toEqual([]);
  });
}
