'use strict';
/* Spoken access and language choice (problem statement features 6 and 8).

   Two rules shape everything here.

   A transcript is a claim about what was said, not a question that was asked. It is
   always shown for correction before it becomes a question, because place names and
   numbers are what a recogniser gets wrong, and a place name chooses which district's
   warning you are shown.

   Only a language this workspace has measured is offered. The service accepts 23
   language codes; far fewer produce a usable answer, and /api/languages reports which.
   Offering the rest would be a promise the workspace cannot keep. */

(function () {
  const TOKEN = (document.querySelector('meta[name="workspace-token"]') || {}).content || '';
  const byId = id => document.getElementById(id);
  const state = { recorder: null, chunks: [], stream: null, speakable: new Set(), busy: false };

  function post(path, body) {
    return fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-WeatherGPT-Token': TOKEN },
      body: JSON.stringify(body)
    }).then(async response => {
      let payload = null;
      try { payload = await response.json(); } catch (error) { payload = null; }
      if (!response.ok) throw new Error((payload && payload.error) || 'That request could not be completed.');
      return payload;
    });
  }

  function say(message) {
    const box = byId('error');
    if (!box) return;
    box.textContent = message;
    box.hidden = !message;
  }

  /* ---------- languages offered are languages measured ---------- */
  async function loadLanguages() {
    const select = byId('language');
    if (!select) return;
    let payload = null;
    try {
      const response = await fetch('/api/languages', { headers: { 'X-WeatherGPT-Token': TOKEN } });
      if (!response.ok) throw new Error('unavailable');
      payload = await response.json();
    } catch (error) {
      // No service, or it could not be read. The question still works; only the
      // choice of answer language goes away, and it says so rather than listing
      // languages that would fail.
      select.title = 'Answering in another language is unavailable on this workspace.';
      return;
    }
    const rows = (payload.languages || []).filter(row => row.measured && row.measured.write === 'verified');
    rows.forEach(row => { if (row.measured.speak === 'verified') state.speakable.add(row.code); });
    rows.sort((a, b) => a.english_name.localeCompare(b.english_name));
    rows.forEach(row => {
      const option = document.createElement('option');
      option.value = row.code;
      option.textContent = row.native_name === row.english_name
        ? row.english_name : row.native_name + ' · ' + row.english_name;
      select.append(option);
    });
    if (!payload.service_configured) {
      select.title = 'No language service key is configured, so answers stay in their source language.';
    }
  }

  /* ---------- press to talk ---------- */
  function micSupported() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);
  }

  function setRecording(on) {
    const mic = byId('mic');
    if (!mic) return;
    mic.classList.toggle('is-recording', on);
    mic.setAttribute('aria-pressed', on ? 'true' : 'false');
    mic.setAttribute('aria-label', on ? 'Stop recording and transcribe' : 'Ask by speaking');
    const busy = byId('busy');
    if (busy) busy.textContent = on ? 'Listening. Press again when you have finished.' : 'Ready';
  }

  function stopStream() {
    if (state.stream) { state.stream.getTracks().forEach(track => track.stop()); state.stream = null; }
  }

  async function startRecording() {
    try {
      state.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (error) {
      say('This page could not use the microphone. Allow microphone access for this local page, or type the question instead.');
      return;
    }
    say('');
    state.chunks = [];
    let recorder;
    try {
      recorder = new MediaRecorder(state.stream);
    } catch (error) {
      stopStream();
      say('This browser cannot record audio here. Type the question instead.');
      return;
    }
    state.recorder = recorder;
    recorder.addEventListener('dataavailable', event => { if (event.data && event.data.size) state.chunks.push(event.data); });
    recorder.addEventListener('stop', () => { stopStream(); transcribe(new Blob(state.chunks, { type: recorder.mimeType || 'audio/webm' })); });
    recorder.start();
    setRecording(true);
  }

  function stopRecording() {
    if (state.recorder && state.recorder.state !== 'inactive') state.recorder.stop();
    state.recorder = null;
    setRecording(false);
  }

  function toBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error('The recording could not be read.'));
      reader.onload = () => {
        const value = String(reader.result || '');
        const comma = value.indexOf(',');
        resolve(comma >= 0 ? value.slice(comma + 1) : value);
      };
      reader.readAsDataURL(blob);
    });
  }

  async function transcribe(blob) {
    const busy = byId('busy');
    if (busy) busy.textContent = 'Working out what was said…';
    try {
      const encoded = await toBase64(blob);
      const type = (blob.type || 'audio/webm').split(';')[0];
      const heard = await post('/api/speech/transcribe', { audio_base64: encoded, content_type: type });
      showTranscript(heard);
    } catch (error) {
      say(error.message || 'That recording could not be transcribed.');
    } finally {
      if (busy) busy.textContent = 'Ready';
    }
  }

  function showTranscript(heard) {
    const panel = byId('transcript');
    const text = byId('transcript-heard');
    const detail = byId('transcript-detail');
    if (!panel || !text) return;
    const transcript = (heard.transcript || '').trim();
    if (!transcript) {
      say('Nothing was recognised in that recording. Try again, or type the question.');
      return;
    }
    text.textContent = transcript;
    if (detail) {
      const parts = [];
      if (heard.detected_language_code) parts.push('Heard as ' + heard.detected_language_code);
      if (typeof heard.recognition_probability === 'number') {
        // The recogniser's own number about which language it heard. It says nothing
        // about whether an answer built from this question would be correct.
        parts.push('recognition confidence ' + heard.recognition_probability.toFixed(2) +
                   ' — this rates the recognition only, not any answer');
      }
      detail.textContent = parts.join(' · ');
    }
    panel.hidden = false;
    const use = byId('transcript-use');
    if (use) use.focus();
  }

  function hideTranscript() {
    const panel = byId('transcript');
    if (panel) panel.hidden = true;
  }

  function putInComposer(andAsk) {
    const text = byId('transcript-heard');
    const question = byId('question');
    if (!text || !question) return;
    question.value = text.textContent || '';
    hideTranscript();
    question.focus();
    question.setSelectionRange(question.value.length, question.value.length);
    if (andAsk) {
      const form = byId('ask-form');
      if (form) form.requestSubmit();
    }
  }

  /* ---------- hearing an answer ---------- */
  function currentLanguage() {
    const select = byId('language');
    const chosen = select && select.value;
    return chosen || 'en';
  }

  async function speak(button, text) {
    if (state.busy) return;
    const language = currentLanguage();
    if (!state.speakable.has(language)) {
      say('This workspace has not verified speech in that language, so it is not offered.');
      return;
    }
    state.busy = true;
    const original = button.textContent;
    button.textContent = 'Preparing…';
    button.disabled = true;
    try {
      const spoken = await post('/api/speech/speak', { text: text.slice(0, 5900), language: language });
      const segments = (spoken.segments || []).map(part => {
        const binary = atob(part);
        const bytes = new Uint8Array(binary.length);
        for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
        return new Blob([bytes], { type: 'audio/' + (spoken.codec || 'wav') });
      });
      await playInOrder(segments, button, original);
    } catch (error) {
      say(error.message || 'That answer could not be read aloud.');
      button.textContent = original;
      button.disabled = false;
      state.busy = false;
    }
  }

  function playInOrder(segments, button, label) {
    return new Promise(resolve => {
      let index = 0;
      const audio = new Audio();
      const urls = segments.map(segment => URL.createObjectURL(segment));
      function done() {
        urls.forEach(url => URL.revokeObjectURL(url));
        button.textContent = label;
        button.disabled = false;
        state.busy = false;
        resolve();
      }
      audio.addEventListener('ended', () => {
        index += 1;
        if (index >= urls.length) return done();
        audio.src = urls[index];
        audio.play().catch(done);
      });
      audio.addEventListener('error', done);
      button.textContent = 'Stop';
      button.disabled = false;
      button.addEventListener('click', function stop() {
        audio.pause();
        button.removeEventListener('click', stop);
        done();
      }, { once: true });
      audio.src = urls[0];
      audio.play().catch(done);
    });
  }

  /* An answer gets a listen control once it is on screen. views.js is left alone:
     it renders evidence, and this is a way of consuming it. */
  function attachListen(turn) {
    if (!turn || turn.querySelector('.listen')) return;
    const copy = turn.querySelector('.answer-copy');
    if (!copy) return;
    const head = turn.querySelector('.turn-head') || turn;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'ghost listen';
    button.textContent = 'Listen';
    button.addEventListener('click', () => {
      const text = Array.from(turn.querySelectorAll('.answer-copy')).map(node => node.textContent).join(' ');
      if (text.trim()) speak(button, text.trim());
    });
    head.append(button);
  }

  function watchThread() {
    const box = byId('thread');
    if (!box || !window.MutationObserver) return;
    const observer = new MutationObserver(() => {
      box.querySelectorAll('.turn-body').forEach(attachListen);
    });
    observer.observe(box, { childList: true, subtree: true });
    box.querySelectorAll('.turn-body').forEach(attachListen);
  }

  /* ---------- wiring ---------- */
  function start() {
    loadLanguages();
    const mic = byId('mic');
    if (mic) {
      if (!micSupported()) {
        mic.disabled = true;
        mic.title = 'This browser cannot record audio on this page. Type the question instead.';
      } else {
        mic.addEventListener('click', () => {
          if (state.recorder) stopRecording(); else startRecording();
        });
      }
    }
    const use = byId('transcript-use');
    if (use) use.addEventListener('click', () => putInComposer(true));
    const edit = byId('transcript-edit');
    if (edit) edit.addEventListener('click', () => putInComposer(false));
    const discard = byId('transcript-discard');
    if (discard) discard.addEventListener('click', () => { hideTranscript(); stopStream(); });
    watchThread();
  }

  /* Exposed for the component checks, which run against a DOM shim with no audio. */
  window.WeatherGPTVoice = { loadLanguages: loadLanguages, showTranscript: showTranscript, hideTranscript: hideTranscript,
                             putInComposer: putInComposer, speak: speak, currentLanguage: currentLanguage, state: state };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
}());
