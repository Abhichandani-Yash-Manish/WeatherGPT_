# Prototype Instructions

## Selected direction — 22 September 2026

The user selected the second displayed Meridian concept, with a calm light theme for evaluators, substantial responsive microinteractions and a gently breathing weather background. Preserve the narrow rail, main answer and evidence margin. All controls are opaque matte; no glassmorphism. This folder is a local interaction prototype using a labelled captured comparison, not the production engine. No readiness tracker changes follow from its visual QA. The original app remains separately available.

Run the local server yourself and open the preview in the browser available to this environment. Do not give the user server-start instructions when you can run it.

Before making substantial visual changes, use the Product Design plugin's `get-context` skill when the visual source is unclear or no longer matches the current goal. When the user gives durable prototype-specific design feedback, preferences, or decisions, record them in `AGENTS.md`.

When implementing from a selected generated mock, treat that image as the source of truth for layout, component anatomy, density, spacing, color, typography, visible content, and hierarchy.

Build app UI in `src/`. Keep `.openai/hosting.json`, `worker/index.js`, `scripts/prepare-sites-build.mjs`, and `tests/sites-worker.test.mjs` intact so the same local prototype can be handed to Sites. Before a Sites handoff, run `npm run build` and `npm run test:sites`; the build must leave `dist/client/index.html`, `dist/server/index.js`, and `dist/.openai/hosting.json`.
