# The UI/UX toolchain

What this machine can now do for design replication and UI verification, how to run each part, and the
tolerance a "flawless" claim is measured against. Written 18 September 2026, from the installed state.

## 1. Design sources → structure and assets

| The question | The tool | State |
| --- | --- | --- |
| What does this reference show, what does its text say? | `vision_glance` (vision model), `vision_long_screenshot_ocr` for tall Figma/spec exports | available |
| Where is the header, the card, the button? | `vision_ground` (one named target), `vision_detect` (every instance of a kind) | available |
| Exact size, offset, shape of a control? | `vision_trace` (measures real pixels, and traces flat art to editable SVG) | available |
| Cut a logo or icon out | `vision_crop` (box), `vision_extract_foreground` (transparent PNG) | available |
| Which colours does the design actually use? | `vision_dominant_colors` (pixel-backed clusters, or score candidate hexes) | available |
| Render a static HTML mock to an image | `vision_html_screenshot` | available |
| How far is my build from the reference? | `vision_pixel_diff` (heatmap + ranked regions) and `tools/fidelity.mjs` locally | available |
| Figma file → frames, images, styles | `tools/figma-pull.mjs` with a **local** token (see §5) | ready, inert without a token |

## 2. Implementation stack already in the project

React 19 + TypeScript + Vite 6 + Tailwind v4, TanStack Query, Motion, Radix popover, `class-variance-authority`
+ `clsx` + `tailwind-merge` (so a shadcn-style component layer is possible without new runtime weight),
`lucide-react` icons, and the app's own component kit in `frontend/src/ui/` over `web/tokens-v2.css`.

**Fonts are local, not CDN:** `@fontsource/ibm-plex-sans`, `ibm-plex-mono`, `noto-serif-gujarati`,
`tiro-devanagari-hindi`, `tiro-bangla`, `tiro-kannada`, `tiro-tamil`, `tiro-telugu`. A design that asks for a
face outside this set needs its files (see §5) — the browser cannot fetch Google Fonts from a sandboxed shell.

## 3. Verification: the harness itself

Installed here: `@playwright/test` 1.63 and `@axe-core/playwright` 4.13 as dev dependencies of `frontend/`,
with Chromium for Testing from Playwright's own cache. `agent-browser` 0.37.1 is installed globally and is the
interactive/exploratory instrument (`agent-browser skills get core`, `... get dogfood`).

```bash
cd frontend
npm run ui:shots      # screenshot every route at the four widths (evidence under research/implementation/ui-evidence)
npm run ui:a11y       # axe over every route: violations, contrast, landmarks
npm run ui:visual     # visual baselines: toHaveScreenshot per route and width
npm run ui:tokens     # extract the live design tokens (colour, type, spacing, radii, shadows, contrast pairs)
npm run ui:diff       # compare captures against a reference directory and write a ranked diff report
```

Environment: `UI_BASE_URL` (default `http://127.0.0.1:8765`), `UI_REFERENCE_DIR` (default
`research/design-references`), `UI_EVIDENCE_DIR` (default `research/implementation/ui-evidence`).

## 4. The replication workflow, and what "flawless" means here

1. **Read the reference** into structure: regions, type scale, palette, spacing, component inventory
   (`vision_glance`, `vision_detect`, `vision_dominant_colors`).
2. **Extract assets** the design needs that the project does not have (`vision_crop`,
   `vision_extract_foreground`, `vision_trace` for flat vector art; `tools/figma-pull.mjs` for a Figma file).
3. **Implement** with the project's tokens and kit; a new component goes into `frontend/src/ui/`, a new surface
   into `frontend/src/modules/` and the registry.
4. **Measure** the build against the reference: `npm run ui:diff` for the ranked deltas and
   `vision_pixel_diff` for the heatmap; `npm run ui:tokens` to compare the palette and type scale the design
   states with the ones the page computes.
5. **Iterate** until the measured deltas are inside tolerance:
   - layout boxes within **±2 px** on the elements that define the grid,
   - colours **exact** against the reference palette (hex, or the pixel-backed cluster the design uses),
   - type scale and weights **exact** where the font is available, otherwise the substitute is named,
   - **zero** axe violations, **zero** horizontal overflow at the four widths,
   - **no** regression in the product: the full gate (`pytest`, `vitest`, `tsc`, build audits, port ledger)
     stays green.
6. **Record** what matches, what deviates and why (`docs/105-design-replication-<name>.md` per pass).

A claim of "flawless" here means: every measurable attribute above is inside tolerance, every state in the
reference is implemented, and the deviation list is empty or explicit. It does not mean the two images are
byte-identical, which no implementation can be while fonts, raster assets or live data differ.

## 5. What needs the reader's input

| Need | Why | Where it goes |
| --- | --- | --- |
| A Figma personal access token | to pull frames, images and styles instead of guessing from a screenshot | `data/runtime/model-config.json` → `"figma_token"` (local, git-ignored, never logged) |
| Font files, if the design uses a face outside §2 | a sandboxed shell cannot fetch Google Fonts; licence terms must allow self-hosting | `frontend/src/assets/fonts/` + a `@font-face` block in the token stylesheet |
| Image/illustration assets | bitmap art cannot be traced faithfully | `frontend/src/assets/` |
| States not visible in a static frame | hover, focus, error, empty, loading, modal stacking, animation timing | one screenshot or a Figma frame per state |
| Behaviour of each control | what a button does when it is not obvious | a sentence per control, or the closest real feature is wired and named |

## 6. What this batch installed, and what it found

**Installed** (all local to the project, no global state, no credentials):

| Package | Version | Why |
| --- | --- | --- |
| `@playwright/test` | 1.63 | the browser harness: screenshots, route assertions, visual baselines, keyboard and click behaviour |
| `@axe-core/playwright` | 4.13 | accessibility over every route, with the `best-practice` tag set as well as WCAG |
| Chromium for Testing | Playwright build 1243 | downloaded to Playwright's own cache; `UI_CHANNEL=chrome` runs the same suite in the Chrome installed on this machine |

npm's shared cache held root-owned files, so installs in this environment use a workspace-local cache:
`npm install --cache ../tmp/npm-cache …`. `tmp/*token*` is git-ignored as a class after a token file reached the
index once.

**Written** (all tracked):

| Path | What it is |
| --- | --- |
| `frontend/playwright.config.ts` | the four widths the brief names, reduced motion, fixed locale and timezone, screenshot diff tolerance |
| `frontend/tests/ui/routes.spec.ts` | every registered route: heading present, no failed request, no console error, no horizontal overflow |
| `frontend/tests/ui/a11y.spec.ts` | axe per route, WCAG 2.0/2.1 A+AA and best practice |
| `frontend/tests/ui/visual.spec.ts` | visual baselines per route (`npm run ui:visual:update` to refresh) |
| `frontend/tests/ui/matrix.spec.ts` | the served engine's district × day matrix: cell roles, the readout, and opening the district a cell belongs to |
| `frontend/tools/capture.mjs` | screenshots every route at the four widths, light and dark, with an overflow and failure report |
| `frontend/tools/tokens.mjs` | the live design tokens (colour, type, spacing, radii, shadows) and the WCAG contrast of every text/background pair |
| `scripts/ui/fidelity.py` | pixel comparison of a rebuild against a reference: size, share differing, mean delta, ranked worst regions, heatmap, palette check |

**First measurements on the running app:**

- `routes.spec.ts`: **19 of 19 pass** in 45 s at 1440 (heading present, no failed request, no console error, no overflow).
- `capture.mjs`: 12 captures over three routes × four widths, **0 overflow, 0 failed requests**.
- `tokens.mjs` on `#overview` @1440: 11 text colours, 24 backgrounds, 3 font stacks, 11 type sizes, **400 text/background pairs measured and 0 below their WCAG threshold**.
- `fidelity.py`, the two controls that prove the tool: the same image compared with itself → **0.00 % differing, mean 0.0/255**; a copy with a 140×60 block recoloured and a 6 px shift → **24–41 % differing in the named regions**, heatmap and `report.json` written.

**Three real defects the harness found, all fixed and re-verified:**

| Defect | Where | Fix | Verified by |
| --- | --- | --- | --- |
| The skip link pointed at `#question` on the 17 surfaces that have no question box — it did nothing, and axe reported "No skip link target"; the link also sat outside every landmark | `frontend/src/App.tsx` | the target is chosen from what the surface has (the question box on Ask and the Dashboard, the main landmark everywhere else), the link has its own `<nav>` landmark, and `<main>` gained `id="main"` + `tabIndex={-1}` | axe: 17 failures → 0 |
| An empty column header in the advisory holdings table | `frontend/src/modules/AdvisoriesSurface.tsx`, `Evidence.tsx` | `DataTable` accepts a heading node; the button column is named for screen readers | axe on `#advisories` passes |
| `role="cell"` on the matrix's clickable buttons — a role a `button` does not allow, on every cell of the served engine's figure | `web/viz.js`, `frontend/src/charts/viz.css` | the cell role moved to a `display: contents` wrapper; the button stays the control | the engine's nine parity checks pass, the new matrix spec passes, axe: 19 of 19 routes clean |

**Accessibility after the fixes:** `npx playwright test tests/ui/a11y.spec.ts` → **19 of 19 routes pass** with
`wcag2a, wcag2aa, wcag21a, wcag21aa, best-practice` at 1440.

## 7. Running the harness

```bash
# one workspace process must be running
python3 -m weathergpt_data.workspace --port 8765

cd frontend
UI_CHANNEL=chrome npx playwright test tests/ui/routes.spec.ts --project=desktop-1440
UI_CHANNEL=chrome npx playwright test tests/ui/a11y.spec.ts --project=desktop-1440
UI_CHANNEL=chrome npx playwright test tests/ui/matrix.spec.ts --project=desktop-1440
UI_CHANNEL=chrome node tools/capture.mjs --only overview,warnings,map --light-only
UI_CHANNEL=chrome node tools/tokens.mjs --route overview --width 1440
python3 ../scripts/ui/fidelity.py --reference <design>.png --capture <rebuild>.png --out <dir>
```

Chromium for Testing is only needed when `UI_CHANNEL` is unset; `npm run ui:install` fetches it.
