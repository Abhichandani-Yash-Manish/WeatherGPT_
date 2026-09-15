// Component-level voice-access checks: measured-language filtering, the confirmable
// transcript and the spoken-language refusal. Not an audio, browser or accuracy test.
'use strict';
const fs = require('fs'), vm = require('vm'), path = require('path'), assert = require('assert');
const shim = require('./dom_shim.js');

const ROOT = path.join(__dirname, '..');
const LANGUAGES = {
  service_configured: true,
  languages: [
    { code: 'en', english_name: 'English', native_name: 'English', measured: { write: 'verified', speak: 'verified' } },
    { code: 'hi', english_name: 'Hindi', native_name: 'हिन्दी', measured: { write: 'verified', speak: 'verified' } },
    { code: 'gu', english_name: 'Gujarati', native_name: 'ગુજરાતી', measured: { write: 'verified', speak: 'unmeasured' } },
    { code: 'ta', english_name: 'Tamil', native_name: 'தமிழ்', measured: { write: 'failed', speak: 'unmeasured' } }
  ]
};

function harness(payloads) {
  const document = shim.createDocument();
  const calls = [];
  const context = Object.create(global);
  const define = (key, value) => Object.defineProperty(context, key, { value: value, writable: true, configurable: true, enumerable: true });
  const window = { addEventListener: () => {}, location: { hash: '' } };
  define('document', document);
  define('window', window);
  define('Node', shim.Node);
  define('navigator', { mediaDevices: null });
  define('fetch', (target, options) => {
    const key = String(target).split('?')[0];
    calls.push({ path: key, body: options && options.body ? JSON.parse(options.body) : null });
    if (payloads[key]) return Promise.resolve({ ok: true, status: 200, json: async () => payloads[key] });
    return Promise.resolve({ ok: false, status: 404, json: async () => ({ error: 'not found' }) });
  });
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(ROOT, 'web/voice.js'), 'utf8'), context);
  return { document, window, calls, voice: () => window.WeatherGPTVoice };
}
function settle(ms) { return new Promise(resolve => setTimeout(resolve, ms === undefined ? 20 : ms)); }

async function run() {
  const h = harness({ '/api/languages': LANGUAGES });
  await settle(30);
  const select = h.document.getElementById('language');
  const options = (select.children || []).map(option => option.value);
  assert.deepEqual(options, ['en', 'gu', 'hi'], 'only measured writable languages are offered, sorted by name: ' + JSON.stringify(options));
  assert(!h.voice().state.speakable.has('gu'), 'a written language without verified speech is not speakable');
  assert(h.voice().state.speakable.has('hi'), 'a verified speech language is speakable');
  console.log('PASS: the language selector offers measured write languages and tracks measured speech');

  h.voice().showTranscript({ transcript: 'कल अहमदाबाद में 35 मिलीमीटर बारिश होगी', detected_language_code: 'hi-IN', recognition_probability: 0.83 });
  const panel = h.document.getElementById('transcript');
  assert.equal(panel.hidden, false, 'a transcript is shown for correction before it becomes a question');
  assert(/35 मिलीमीटर/.test(h.document.getElementById('transcript-heard').textContent), 'the recognised text is shown as heard');
  const detail = h.document.getElementById('transcript-detail').textContent;
  assert(/Heard as hi-IN/.test(detail), 'the detected language is stated');
  assert(/recognition confidence 0.83/.test(detail) && /not any answer/.test(detail), 'recognition confidence is labelled as recognition only: ' + detail);
  const composer = h.document.getElementById('question');
  composer.focus = () => {};
  composer.setSelectionRange = () => {};
  h.document.getElementById('ask-form').requestSubmit = () => {};
  h.document.getElementById('transcript-use').dispatch('click');
  assert.equal(h.document.getElementById('question').value, 'कल अहमदाबाद में 35 मिलीमीटर बारिश होगी', 'using the transcript puts the heard text in the composer');
  assert.equal(panel.hidden, true, 'the transcript panel closes once used');
  console.log('PASS: a transcript is shown, labelled with recognition-only confidence, and confirmable');

  select.value = 'gu';
  const button = h.document.createElement('button');
  await h.voice().speak(button, 'Some answer text');
  assert(/has not verified speech in that language/.test(h.document.getElementById('error').textContent), 'speech is refused where it was not measured');
  assert(!h.calls.some(call => call.path === '/api/speech/speak'), 'no speech request is sent for an unmeasured language');
  console.log('PASS: speech is refused, not guessed, where the project has not measured it');

  process.exit(0);
}
run().catch(error => { console.error(error); process.exit(1); });
