/* The district x day matrix, the figure the served engine draws into the Warnings surface. Three things must
   hold after the cell-role fix (18 September 2026): the cell is a button inside a named cell, a cell is
   reachable and reads its own district/day/colour, and choosing one opens that district below the figure. */
import { expect, test } from '@playwright/test';

test.describe('the district x day matrix', () => {
  test('names every cell and opens the district a cell belongs to', async ({ page }) => {
    await page.goto('/#/warnings', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('main')).toBeVisible({ timeout: 30_000 });
    const matrix = page.locator('.viz-matrix');
    await expect(matrix).toBeVisible({ timeout: 30_000 });

    const cells = matrix.locator('.viz-cell');
    const count = await cells.count();
    expect(count, 'the matrix must draw at least one district-day cell').toBeGreaterThan(0);

    /* Roles: the cell role is on the wrapper, the control inside it is a button. */
    const first = cells.first();
    await expect(first).toHaveRole('button');
    await expect(first.locator('xpath=..')).toHaveAttribute('role', 'cell');
    await expect(first).not.toHaveAttribute('role', 'cell');

    /* The name carries the district, the day and the colour the product printed. */
    const label = await first.getAttribute('aria-label');
    expect(label).toMatch(/Day \d/);
    expect(label).toMatch(/colour (red|orange|yellow|green)|no colour stated by the product/);

    /* Focusing a cell reads it out, and choosing one opens that district below the figure. */
    await first.focus();
    await expect(page.locator('.viz-matrix-block .viz-readout')).not.toHaveText('');
    const district = (await first.getAttribute('aria-label')).split(',')[0].trim();
    await first.click();
    const opened = page.locator('[data-testid=warnings-district]');
    await expect(opened).toBeVisible({ timeout: 15_000 });
    await expect(opened).toContainText(district, { ignoreCase: true });
  });
});
