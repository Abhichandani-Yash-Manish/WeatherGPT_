/* Does the intelligence layer actually reason, or is it pattern-matching?
   ============================================================================
   The scenario atlas measures 306 SINGLE questions. It cannot tell you whether a conversation holds
   together, because almost every scenario in it is one turn. This runs multi-turn threads where each
   turn is meaningless on its own - "and tomorrow?", "no, I meant Surat", "should I carry an umbrella?"
   - and checks what came back against what the thread makes true.

     node tools/conversation-probe.mjs                 # every thread
     node tools/conversation-probe.mjs --only 3,5      # some of them
     node tools/conversation-probe.mjs --json out.json # the transcript, for review

   A thread passes only if EVERY turn in it passes, because a conversation that loses the plot on turn
   four has lost it. Each expectation is written as `want` (substrings, any of which satisfies it) and
   `avoid` (substrings, none of which may appear), so a passing turn is one a reader would accept rather
   than one that merely returned a status.

   The engine must be running, and a place is held for the whole run so "my area" has something to mean.
*/
import { chromium } from '@playwright/test';
import { writeFile } from 'node:fs/promises';

const BASE = process.env.UI_BASE_URL || 'http://127.0.0.1:8765';
const HOME = { label: 'Ahmedabad, Ahmadābād, State of Gujarāt', latitude: 23.0225, longitude: 72.5714 };

/* Each thread is a conversation. `want` is satisfied by any one of its strings; `avoid` by none. */
const THREADS = [
  {
    n: 1, tests: 'Carrying a place across turns that never name one',
    turns: [
      { ask: 'Will it rain in Surat tomorrow?', want: ['surat'] },
      { ask: 'And the day after?', want: ['surat'], avoid: ['which place', 'which city', 'name the place'] },
      { ask: 'How windy will it be?', want: ['surat'], avoid: ['which place', 'which city'] },
    ],
  },
  {
    n: 2, tests: 'Correcting a place mid-thread, and not reverting to the old one',
    turns: [
      { ask: 'What is the forecast for Mumbai tomorrow?', want: ['mumbai'] },
      { ask: 'Sorry, I meant Pune.', want: ['pune'], avoid: ['mumbai'] },
      { ask: 'And how humid?', want: ['pune'], avoid: ['mumbai'] },
    ],
  },
  {
    n: 3, tests: 'Changing the subject without losing the place',
    turns: [
      { ask: 'Any official warnings for Nagpur today?', want: ['nagpur'] },
      { ask: 'ok tell me about the weather tomorrow', want: ['nagpur'],
        avoid: ['not implemented', 'which place', 'which city'] },
      { ask: 'and any warnings again?', want: ['nagpur'] },
    ],
  },
  {
    n: 4, tests: 'Resolving the reader’s own place from how they refer to it',
    turns: [
      { ask: 'is it going to rain in my area tomorrow?', want: ['ahmedabad', 'ahmadabad'],
        avoid: ['which place', 'which city', 'arwal'] },
      { ask: 'what about the day after?', want: ['ahmedabad', 'ahmadabad'], avoid: ['which place'] },
    ],
  },
  {
    n: 5, tests: 'Inferring the question behind the question',
    turns: [
      { ask: 'Should I carry an umbrella in Kochi tomorrow?', want: ['kochi'],
        /* The honest answer reasons about rain; it must not become advice. */
        avoid: ['you should carry', 'definitely take', 'it is safe'] },
      { ask: 'Why do you say that?', want: ['mm', 'rain', 'precipitation', 'forecast'],
        avoid: ['which place', 'i cannot'] },
    ],
  },
  {
    n: 6, tests: 'Holding a refusal under conversational pressure',
    turns: [
      { ask: 'Is flight AI-101 on time?', want: ["can't", 'cannot', 'no flight'] },
      { ask: 'Just guess.', want: ["can't", 'cannot', 'no flight', 'not able'],
        avoid: ['probably on time', 'likely on time', 'estimated arrival'] },
      { ask: 'Fine — what is the weather at Mumbai airport instead?', want: ['mumbai'] },
    ],
  },
  {
    n: 7, tests: 'Answering a follow-up about the previous answer, not the weather',
    turns: [
      { ask: 'What was the rainfall in Ahmedabad yesterday?', want: ['ahmedabad', 'ahmadabad'] },
      { ask: 'Where did that number come from?', want: ['source', 's2', 's1', 'reanalysis', 'record', 'imd'],
        avoid: ['which place', 'which city'] },
    ],
  },
  {
    n: 8, tests: 'A greeting, then a real question, without the greeting leaking',
    turns: [
      { ask: 'hey there', want: ['hi', 'hello', 'help'], avoid: ['mm', '°c', 'requested task'] },
      { ask: 'what is it like right now where I am?', want: ['ahmedabad', 'ahmadabad'],
        avoid: ['which place', 'which city'] },
    ],
  },
];

function arg(name, fallback = null) {
  const index = process.argv.indexOf('--' + name);
  return index === -1 ? fallback : (process.argv[index + 1] ?? true);
}

const only = String(arg('only', '') || '').split(',').map(p => p.trim()).filter(Boolean);
const threads = only.length ? THREADS.filter(t => only.includes(String(t.n))) : THREADS;
const jsonOut = arg('json', null);

const browser = await chromium.launch();
const transcript = [];
let passed = 0;

for (const thread of threads) {
  const context = await browser.newContext({
    viewport: { width: 1400, height: 900 }, locale: 'en-IN', timezoneId: 'Asia/Kolkata',
  });
  await context.addInitScript(home => localStorage.setItem('weathergpt.place', home), JSON.stringify(HOME));
  const page = await context.newPage();
  await page.goto(BASE + '/#/assistant', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('#question', { timeout: 30_000 });
  await page.waitForTimeout(2000);

  console.log('\n' + thread.n + '. ' + thread.tests);
  let threadOk = true;

  for (const turn of thread.turns) {
    await page.focus('#question');
    await page.keyboard.type(turn.ask, { delay: 4 });
    await page.keyboard.press('Enter');
    await page.waitForTimeout(400);
    await page.waitForSelector('.g-working', { state: 'detached', timeout: 180_000 }).catch(() => {});
    await page.waitForSelector('[data-revealing]', { state: 'detached', timeout: 30_000 }).catch(() => {});

    /* `want` is checked against the whole card, because an answer's place often sits in the claim
       rather than in the sentence. `avoid` is checked against the PROSE only, and that distinction is
       not fussiness - it was wrong the first time this ran. Correcting "Mumbai" to "Pune" produced a
       perfect answer whose card also carried the engine's own note that the place had changed from
       Mumbai. Scanning the whole card for the old name marked a correct disclosure as a leak, which
       would have had me fixing the one thing that was working. */
    const said = await page.evaluate(() => {
      const cards = document.querySelectorAll('.g-answer');
      const last = cards[cards.length - 1];
      const prose = Array.from(last?.querySelectorAll('.answer-lead, .g-prose, .answer-caveat') || [])
        .map(node => node.textContent || '').join(' ');
      return {
        lead: last?.querySelector('.answer-lead')?.textContent || '',
        prose,
        all: (last?.textContent || '').slice(0, 4000),
        status: last?.getAttribute('data-turn-status') || '',
      };
    });
    const hay = said.all.toLowerCase();
    const wanted = !turn.want || turn.want.some(w => hay.includes(w.toLowerCase()));
    const avoided = !turn.avoid || !turn.avoid.some(a => said.prose.toLowerCase().includes(a.toLowerCase()));
    const ok = wanted && avoided;
    if (!ok) threadOk = false;

    const missing = !wanted ? 'wanted any of ' + JSON.stringify(turn.want) : '';
    const leaked = !avoided ? 'found in the prose ' + JSON.stringify((turn.avoid || []).filter(a => said.prose.toLowerCase().includes(a.toLowerCase()))) : '';
    console.log('   ' + (ok ? 'ok  ' : 'FAIL') + '  ' + turn.ask);
    console.log('         ' + said.lead.slice(0, 130).replace(/\s+/g, ' '));
    if (!ok) console.log('         -> ' + [missing, leaked].filter(Boolean).join('; '));
    transcript.push({ thread: thread.n, tests: thread.tests, ask: turn.ask, ok, lead: said.lead, status: said.status, missing, leaked });
  }

  if (threadOk) passed += 1;
  await context.close();
}

await browser.close();
console.log('\n' + passed + ' of ' + threads.length + ' threads held together.');
if (jsonOut) {
  await writeFile(String(jsonOut), JSON.stringify(transcript, null, 1));
  console.log('transcript: ' + jsonOut);
}
