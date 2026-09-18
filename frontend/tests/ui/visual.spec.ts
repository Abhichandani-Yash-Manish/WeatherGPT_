/* Visual baselines: one screenshot per route and viewport, compared against the stored baseline.
   Generate or refresh them with `npm run ui:visual:update` and review the diff before committing. */
import { expect, test } from '@playwright/test';
import { VIEWS } from '../../src/shell/views';

test.describe.configure({ mode: 'serial' });

for (const route of VIEWS.map(view => view.id)) {
  test('#' + route + ' matches its visual baseline', async ({ page }, testInfo) => {
    await page.goto('/#/' + route, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('main')).toBeVisible({ timeout: 30_000 });
    /* Motion and the aurora field are pinned by reducedMotion; this waits out the last fade. */
    await page.waitForTimeout(2000);
    await expect(page).toHaveScreenshot(['baseline', route + '.png'], { fullPage: false, animations: 'disabled', caret: 'hide', scale: 'css' });
  });
}
