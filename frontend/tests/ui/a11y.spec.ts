/* axe over every route: violations, in the four categories that matter for a weather desk (contrast, names,
   landmarks, structure). A violation fails the run; the report names the rule and the element. */
import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';
import { VIEWS } from '../../src/shell/views';

/* The front door is not a route in the registry — it is the empty address — so it is named here. A front
   door that fails the contrast or landmark gate is the first thing a reader meets and the last thing the
   route loop would catch. */
test('the front door has no axe violation', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('h1')).toBeVisible({ timeout: 30_000 });
  await page.waitForTimeout(2000);
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'])
    .analyze();
  const summary = results.violations.map(violation => ({
    rule: violation.id, impact: violation.impact, help: violation.help,
    nodes: violation.nodes.slice(0, 3).map(node => node.target.join(' ')),
  }));
  expect(summary, 'axe violations on the front door').toEqual([]);
});

for (const route of VIEWS.map(view => view.id)) {
  test('#' + route + ' has no axe violation', async ({ page }) => {
    await page.goto('/#/' + route, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('main')).toBeVisible({ timeout: 30_000 });
    await page.waitForTimeout(1500);

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'])
      .analyze();

    const summary = results.violations.map(violation => ({
      rule: violation.id, impact: violation.impact, help: violation.help,
      nodes: violation.nodes.slice(0, 3).map(node => node.target.join(' ')),
    }));
    expect(summary, 'axe violations on #' + route).toEqual([]);
  });
}
