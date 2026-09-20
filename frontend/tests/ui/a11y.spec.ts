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

/* The place's own page is a shell route, not a VIEWS entry (docs/122), so the loop above cannot reach it -
   and the front door test cannot either, because it has an address of its own. Both of its states are checked:
   a page that names a place, and the page a reader lands on when the address is half-written. The second one
   still has to be readable and navigable, because being refused is not the same thing as being broken. */
const PLACE_ADDRESSES = [
  '#/place?place=Kochi,%20Kerala&plat=9.93&plon=76.26',
  '#/place?place=Kochi,%20Kerala&plat=9.93',
];

for (const address of PLACE_ADDRESSES) {
  test(address + ' has no axe violation', async ({ page }) => {
    await page.goto('/' + address, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('main')).toBeVisible({ timeout: 30_000 });
    await page.waitForTimeout(1500);

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'])
      .analyze();

    const summary = results.violations.map(violation => ({
      rule: violation.id, impact: violation.impact, help: violation.help,
      nodes: violation.nodes.slice(0, 3).map(node => node.target.join(' ')),
    }));
    expect(summary, 'axe violations on ' + address).toEqual([]);
  });
}

