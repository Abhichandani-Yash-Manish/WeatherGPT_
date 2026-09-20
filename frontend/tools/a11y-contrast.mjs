/* What the page actually computes for the nodes axe complained about, and WHICH RULE sets it.
   ============================================================================
   The first version reported a node's computed ink and walked up for an opaque background colour - and a card
   drawn with a background-image gradient has a transparent background-color, so it reported the page ground and
   rated a failing header as passing. It also could not say which stylesheet rule won. This version lists every
   matching rule that sets a colour, in cascade order, so the rule to fix is named rather than guessed at. */
import { chromium } from '@playwright/test';

const BASE = process.env.UI_BASE_URL || 'http://127.0.0.1:8765';
const SELECTORS = process.env.UI_SELECTORS ? process.env.UI_SELECTORS.split(',') : ['.dash-map-zoom'];
const ROUTE = process.env.UI_ROUTE || 'overview';

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 833 }, reducedMotion: 'reduce' });
await page.goto(BASE + '/#/' + ROUTE, { waitUntil: 'domcontentloaded' });
await page.waitForTimeout(2500);

const report = await page.evaluate(selectors => selectors.map(selector => {
  const node = document.querySelector(selector);
  if (!node) return { selector, missing: true };
  const winners = [];
  const walk = (list, media, sheet) => {
    for (const rule of list) {
      if (rule.cssRules !== undefined && rule.selectorText === undefined) { walk(rule.cssRules, rule.conditionText || media, sheet); continue; }
      if (!rule.selectorText || !rule.style) continue;
      const colour = rule.style.getPropertyValue('color');
      if (!colour) continue;
      let matches = false;
      try { matches = node.matches(rule.selectorText); } catch (error) { matches = false; }
      if (matches) winners.push({ selector: rule.selectorText, color: colour, media: media || null, sheet: sheet });
    }
  };
  for (const sheet of document.styleSheets) {
    let rules = null;
    try { rules = sheet.cssRules; } catch (error) { continue; }
    const name = sheet.href ? sheet.href.split('/').pop() : 'inline';
    walk(rules, null, name);
  }
  const style = getComputedStyle(node);
  return { selector, colour: style.color, background: style.backgroundColor,
    fontSize: style.fontSize, fontWeight: style.fontWeight, winners };
}), SELECTORS);
console.log(JSON.stringify(report, null, 1));
await browser.close();
