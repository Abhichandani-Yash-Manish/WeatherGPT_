/* The demo, driven and recorded.
   ============================================================================
   A scripted run through the eight key features of SIH26068, against the REAL engine: every turn below
   is planned, retrieved and written live, and the video is whatever actually happened. Nothing here is a
   mock, a fixture or a replay, which is the point - a backup video of a rehearsed demo is only worth
   having if it is a recording of the demo rather than an advertisement for it.

     node tools/demo.mjs                      # every beat, recorded to research/demo/
     node tools/demo.mjs --only 4,9           # a subset, by number
     node tools/demo.mjs --list               # print the running order and exit
     node tools/demo.mjs --out /tmp/demo      # somewhere else
     node tools/demo.mjs --no-video           # drive it without recording

   The app must already be running:
       python3 -m weathergpt_data.workspace --port 8765

   TIMING. Each beat waits for the turn to finish AND for the answer to finish being written onto the
   page, then holds for a beat so a viewer can read it. It does not hurry: a demo video that moves faster
   than a judge can read is a demo video of nothing. Expect roughly fifteen seconds a beat.
*/
import { chromium } from '@playwright/test';
import { mkdir, rename, readdir } from 'node:fs/promises';
import path from 'node:path';

const BASE = process.env.UI_BASE_URL || 'http://127.0.0.1:8765';

/* The running order. Each beat names the SIH key feature it demonstrates, so the video and the problem
   statement can be read side by side, and says what a viewer should be looking at. */
const BEATS = [
  { n: 1, feature: 'KF1 real-time retrieval',
    ask: 'What is it like right now in Ahmedabad?',
    watch: 'A station reading, with the station named and how far away it is.' },
  { n: 2, feature: 'KF2 natural-language forecast',
    ask: 'Will it rain in Mumbai tomorrow?',
    watch: 'Plain question, plain answer, and the value carries its window and its source.' },
  { n: 3, feature: 'KF3 NWP models (GFS)',
    ask: 'Compare the GFS and best-match forecasts for Pune tomorrow.',
    watch: 'Two named models, and the answer says where they disagree rather than averaging them.' },
  { n: 4, feature: 'KF4 warnings and early warning',
    ask: 'Which districts in Odisha have a warning today, and in what colour?',
    watch: 'The publisher’s own colours. An absence of guidance is never drawn as an all-clear.' },
  { n: 5, feature: 'KF5 location-based advisory',
    ask: 'What does the agromet advisory say for Ahmedabad?',
    watch: 'The bulletin’s own words, quoted, with the edition and the date it was issued.' },
  { n: 6, feature: 'KF6 Indian languages',
    ask: 'अहमदाबाद में कल बारिश होगी क्या?',
    watch: 'Answered in the script it was asked in. Numbers, units and place names are not translated.' },
  { n: 7, feature: 'KF7 climate and history',
    ask: 'Which year was the wettest in the record for India?',
    watch: 'A year and a figure from the published record, not a range and not a guess.' },
  { n: 8, feature: 'KF8 evidence under the answer',
    ask: 'Where did that number come from?',
    /* Typed into the SAME conversation rather than opened fresh, because the thing being shown is that
       "that number" is understood - which a new page could not possibly demonstrate. */
    followsOn: true,
    watch: 'The follow-up is understood in context, and every value is traceable to its source.' },
  /* The two that judges remember, because most demos cannot do them. */
  { n: 9, feature: 'Refusal discipline',
    ask: 'Is flight AI-101 on time?',
    watch: 'It says it cannot, and why. It does not invent a plausible answer.' },
  { n: 10, feature: 'Refusal discipline',
    ask: 'Is it safe to go out in Chennai right now?',
    watch: 'It gives the conditions and declines the safety judgement it has no basis to make.' },
];

function arg(name, fallback = null) {
  const index = process.argv.indexOf('--' + name);
  return index === -1 ? fallback : (process.argv[index + 1] ?? true);
}

if (arg('list', false)) {
  for (const beat of BEATS) console.log(String(beat.n).padStart(2), '|', beat.feature.padEnd(32), '|', beat.ask);
  process.exit(0);
}

const only = String(arg('only', '') || '').split(',').map(part => part.trim()).filter(Boolean);
const beats = only.length ? BEATS.filter(beat => only.includes(String(beat.n))) : BEATS;
const outDir = path.resolve(String(arg('out', '../research/demo')));
const video = !arg('no-video', false);
const hold = Number(arg('hold', 3500));

await mkdir(outDir, { recursive: true });

const browser = await chromium.launch({ channel: process.env.UI_CHANNEL || undefined });
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2,
  locale: 'en-IN', timezoneId: 'Asia/Kolkata',
  ...(video ? { recordVideo: { dir: outDir, size: { width: 1440, height: 900 } } } : {}),
});
const page = await context.newPage();

const failures = [];
page.on('console', message => { if (message.type() === 'error') failures.push(message.text().slice(0, 140)); });

await page.goto(BASE + '/#/assistant', { waitUntil: 'domcontentloaded' });
await page.waitForSelector('#question', { timeout: 30_000 });

console.log('Recording' + (video ? ' to ' + outDir : ' disabled') + '\n');
const started = Date.now();
const transcript = [];

for (const beat of beats) {
  const at = Date.now();
  process.stdout.write(String(beat.n).padStart(2) + '  ' + beat.feature.padEnd(32) + '  ');
  if (!beat.followsOn || !transcript.length) {
    /* A NEW CONVERSATION, then the question typed into the box.
       This used to seed each beat through `?ask=` in the address. It does not work and it fails
       silently: changing only the hash fragment does not reload a single-page app, so the seed is
       never read and the app simply restores the conversation already on screen. Measured 21 September
       2026 - beat 1 took 47s and ran for real, beats 2 to 7 took 5.5s each and every one of them
       reported beat 1's answer about Ahmedabad.

       Driving the controls is also what the demo itself is: nobody presents this by editing a URL. */
    await page.evaluate(() => {
      const control = Array.from(document.querySelectorAll('button'))
        .find(node => (node.textContent || '').includes('New conversation'));
      control?.click();
    });
    await page.waitForTimeout(700);
  }
  {
    /* Asked where the reader would ask it: in the box, under the answer it refers to. */
    /* Focused rather than clicked. The page's ambient field never stops moving, so Playwright's
       actionability check waits for a "stable" box that never arrives and times out on a control that
       was ready the whole time. Focus takes no such check.

       Then typed key by key, not filled: `fill()` assigns a value, which leaves the send button disabled
       because the composer enables it from React state - and on a recording, a question that appears all
       at once looks like a cut rather than like someone asking. Enter is what the composer binds. */
    await page.focus('#question');
    await page.keyboard.type(beat.ask, { delay: 28 });
    await page.waitForTimeout(400);
    await page.keyboard.press('Enter');
  }
  await page.waitForSelector('main', { timeout: 30_000 }).catch(() => {});
  /* The turn finishes, and THEN the answer finishes being written. Waiting only for the first
     photographs - and records - a sentence caught halfway through. */
  await page.waitForTimeout(400);
  await page.waitForSelector('.g-working', { state: 'detached', timeout: 180_000 }).catch(() => {});
  await page.waitForSelector('[data-revealing]', { state: 'detached', timeout: 30_000 }).catch(() => {});
  /* The LAST answer on the page, not the first. A follow-up is asked in the same thread, so reading
     `querySelector` reports the answer above it and every beat after the first looks like a repeat. */
  const answer = await page.evaluate(() => {
    const leads = document.querySelectorAll('.answer-lead');
    const cards = document.querySelectorAll('.g-answer');
    return {
      lead: leads[leads.length - 1]?.textContent || '',
      status: cards[cards.length - 1]?.getAttribute('data-turn-status') || '',
    };
  });
  /* Held so a viewer can actually read it, then scrolled through the evidence beneath it. */
  await page.waitForTimeout(hold);
  await page.evaluate(async () => {
    const thread = document.querySelector('.g-thread');
    if (!thread) return;
    const end = thread.scrollHeight;
    for (let y = thread.scrollTop; y < end; y += 220) {
      thread.scrollTo({ top: y }); await new Promise(r => setTimeout(r, 90));
    }
  });
  await page.waitForTimeout(1200);
  const seconds = Math.round((Date.now() - at) / 100) / 10;
  console.log(String(seconds).padStart(5) + 's  ' + (answer.status || 'no answer').padEnd(16) + answer.lead.slice(0, 64));
  transcript.push({ ...beat, seconds, ...answer });
}

await context.close();
await browser.close();

/* Playwright names a video after the page's internal id; the file is renamed to something a person
   looking for the demo recording would recognise. */
if (video) {
  const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  for (const name of await readdir(outDir)) {
    if (!name.endsWith('.webm') || name.startsWith('weathergpt-demo')) continue;
    await rename(path.join(outDir, name), path.join(outDir, 'weathergpt-demo-' + stamp + '.webm'));
  }
}

console.log('\n' + beats.length + ' beats in ' + Math.round((Date.now() - started) / 1000) + 's');
const missing = transcript.filter(row => !row.lead);
if (missing.length) console.log('NO ANSWER on beat(s): ' + missing.map(row => row.n).join(', '));
if (failures.length) console.log('console errors: ' + failures.length + ' - ' + failures[0]);
if (video) console.log('video: ' + outDir);
