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

/* The place's own page (docs/122) is a SHELL route rather than a surface: it has no module renderer, no rail
   row and no single product route, so it is not a VIEWS entry and the loop above cannot reach it. Naming it
   here is what puts it inside the same checks every surface gets - the heading, the failed requests, the
   console errors and the overflow - because a page nobody measures is a page nobody has looked at.

   Two addresses, because both are pages a reader can land on. The half-written one must make NO READ AT ALL,
   which is the address's own rule, so it is asserted as an absence of requests rather than as an absence of
   errors: an address that is refused before any read is a different thing from a read that failed. */
const PLACE_ADDRESSES = [
  { name: 'a named place', hash: '#/place?place=Kochi,%20Kerala&plat=9.93&plon=76.26', heading: 'Kochi, Kerala', reads: true },
  { name: 'a half-written address', hash: '#/place?place=Kochi,%20Kerala&plat=9.93', heading: 'No place to show', reads: false },
];

for (const address of PLACE_ADDRESSES) {
  test('#/place with ' + address.name + ' states its heading and makes only the reads it should', async ({ page }) => {
    const failures: string[] = [];
    const consoleErrors: string[] = [];
    const reads: string[] = [];
    page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text().slice(0, 200)); });
    page.on('response', response => { if (response.status() >= 400) failures.push(response.status() + ' ' + response.url()); });
    page.on('request', request => { if (request.url().includes('/api/')) reads.push(request.url()); });

    await page.goto('/' + address.hash, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('main')).toBeVisible({ timeout: 30_000 });
    const heading = page.locator('main h1').first();
    await expect(heading).toBeVisible({ timeout: 20_000 });
    await expect(heading).toHaveText(address.heading);

    await page.waitForTimeout(1500);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, 'horizontal overflow in px at ' + address.hash).toBeLessThanOrEqual(1);
    expect(failures, 'failed requests on ' + address.hash).toEqual([]);
    expect(consoleErrors, 'console errors on ' + address.hash).toEqual([]);
    if (address.reads) {
      expect(reads.length, 'a valid place address must read the place: ' + address.hash).toBeGreaterThan(0);
    } else {
      expect(reads, 'a refused address must make no read at all: ' + address.hash).toEqual([]);
    }
  });
}

