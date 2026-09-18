/* Extract the design tokens the running page actually computes: colour, type, spacing, radii, shadows, the
   fonts in use, and the contrast of every text/background pair on the page. This is what a replicated design
   is measured against — a reference screenshot states a palette, this states what the browser resolved.

     node tools/tokens.mjs --route overview --width 1440 [--out file.json]

   The app must already be running; see tools/capture.mjs for why. */
import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const BASE = process.env.UI_BASE_URL || 'http://127.0.0.1:8765';
function arg(name, fallback = null) {
  const index = process.argv.indexOf('--' + name);
  return index === -1 ? fallback : (process.argv[index + 1] ?? true);
}
const route = String(arg('route', 'overview'));
const width = Number(arg('width', 1440));
const out = path.resolve(String(arg('out', '../research/implementation/ui-evidence/tokens-' + route + '@' + width + '.json')));

/* UI_CHANNEL=chrome drives the browser installed on this machine; otherwise Playwright's own Chromium. */
const CHANNEL = process.env.UI_CHANNEL || undefined;
const browser = await chromium.launch(CHANNEL ? { channel: CHANNEL } : {});
const context = await browser.newContext({ viewport: { width, height: 900 }, deviceScaleFactor: 1, colorScheme: 'light', reducedMotion: 'reduce', locale: 'en-IN', timezoneId: 'Asia/Kolkata' });
const page = await context.newPage();
await page.goto(BASE + '/#/' + route, { waitUntil: 'domcontentloaded' });
await page.waitForSelector('main', { timeout: 30_000 }).catch(() => {});
await page.waitForTimeout(1500);

const audit = await page.evaluate(() => {
  const seen = (map, value) => { if (value) map[value] = (map[value] || 0) + 1; };
  const colours = {}, backgrounds = {}, borders = {}, fonts = {}, sizes = {}, weights = {}, radii = {}, shadows = {}, spacing = {};
  const nodes = Array.from(document.querySelectorAll('body *'));
  const parseRgb = value => {
    const match = /rgba?\(([^)]+)\)/.exec(value || '');
    if (!match) return null;
    const parts = match[1].split(',').map(part => parseFloat(part));
    return { r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1 };
  };
  const luminance = ({ r, g, b }) => {
    const channel = value => { const c = value / 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
  };
  const hex = ({ r, g, b, a }) => a < 1 ? 'rgba(' + r + ',' + g + ',' + b + ',' + a + ')' : '#' + [r, g, b].map(v => Math.round(v).toString(16).padStart(2, '0')).join('');
  const contrast = [];
  for (const node of nodes) {
    const style = getComputedStyle(node);
    seen(colours, style.color);
    if (style.backgroundColor && style.backgroundColor !== 'rgba(0, 0, 0, 0)') seen(backgrounds, style.backgroundColor);
    if (style.borderTopColor && style.borderTopWidth !== '0px') seen(borders, style.borderTopColor);
    seen(fonts, style.fontFamily);
    seen(sizes, style.fontSize);
    seen(weights, style.fontWeight);
    if (style.borderRadius && style.borderRadius !== '0px') seen(radii, style.borderRadius);
    if (style.boxShadow && style.boxShadow !== 'none') seen(shadows, style.boxShadow);
    const rect = node.getBoundingClientRect();
    if (rect.width > 40 && rect.height > 8) {
      seen(spacing, [style.paddingTop, style.paddingRight, style.paddingBottom, style.paddingLeft].join(' '));
      if (style.gap && style.gap !== 'normal') seen(spacing, 'gap ' + style.gap);
      const text = (node.textContent || '').trim();
      if (text && node.children.length === 0) {
        const foreground = parseRgb(style.color);
        let parent = node, background = null;
        while (parent && !background) {
          const candidate = parseRgb(getComputedStyle(parent).backgroundColor);
          if (candidate && candidate.a > 0.5) background = candidate;
          parent = parent.parentElement;
        }
        if (foreground && background) {
          const lighter = Math.max(luminance(foreground), luminance(background));
          const darker = Math.min(luminance(foreground), luminance(background));
          const ratio = (lighter + 0.05) / (darker + 0.05);
          const size = parseFloat(style.fontSize);
          const bold = parseInt(style.fontWeight, 10) >= 700;
          const large = size >= 24 || (size >= 18.66 && bold);
          const required = large ? 3 : 4.5;
          if (contrast.length < 400) contrast.push({ text: text.slice(0, 40), colour: hex(foreground), background: hex(background), ratio: Math.round(ratio * 100) / 100, required, passes: ratio + 0.005 >= required, size, weight: style.fontWeight });
        }
      }
    }
  }
  const top = map => Object.entries(map).sort((a, b) => b[1] - a[1]).slice(0, 24).map(([value, count]) => ({ value, count }));
  return {
    url: location.href,
    tokens: {
      colours: top(colours), backgrounds: top(backgrounds), borders: top(borders),
      fonts: top(fonts), sizes: top(sizes), weights: top(weights), radii: top(radii), shadows: top(shadows), spacing: top(spacing),
    },
    contrast,
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  };
});

await browser.close();
const failing = audit.contrast.filter(row => !row.passes);
const result = { ...audit, contrast_failures: failing };
await mkdir(path.dirname(out), { recursive: true });
await writeFile(out, JSON.stringify(result, null, 1));
console.log('wrote', out);
console.log('distinct colours:', result.tokens.colours.length, '| backgrounds:', result.tokens.backgrounds.length, '| font stacks:', result.tokens.fonts.length, '| type sizes:', result.tokens.sizes.length);
console.log('text/background pairs measured:', audit.contrast.length, '| below their WCAG threshold:', failing.length);
for (const row of failing.slice(0, 6)) console.log('   ', row.ratio, 'needs', row.required, '|', row.colour, 'on', row.background, '|', row.text);
console.log('horizontal overflow at', width + 'px:', audit.overflow);
process.exit(failing.length ? 1 : 0);
