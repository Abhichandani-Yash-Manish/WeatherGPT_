import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, MotionConfig, motion, useReducedMotion } from 'motion/react';
import { ArrowUp, ArrowRight, Bell, Check, ChevronDown, Copy, ExternalLink, History, MapPin, MessageSquare, Mic, Pause, Play, Plus, RotateCcw, Settings2, Square, X } from 'lucide-react';
import '@fontsource-variable/inter';
import '@fontsource/ibm-plex-mono/400.css';

const QUESTION = 'Compare the rainfall forecast for Surat and Vadodara tomorrow morning.';
const WINDOW = '23 Sep 2026 · 09:30–12:30 IST';
const SOURCES = [
  { id: 'S62', name: 'Open-Meteo best-match', values: ['0.4', '0.2'], url: 'https://open-meteo.com/en/docs', detail: 'Best-match may include GFS upstream. These products are not independent confirmations.' },
  { id: 'S21', name: 'GFS', values: ['0.0', '0.0'], url: 'https://open-meteo.com/en/docs/gfs-api', detail: 'GFS model forecast served through Open-Meteo. Values describe the selected points and accumulation window.' },
];
const stages = ['Reading the saved question', 'Opening the two captured sources', 'Preparing the saved comparison'];
const followups = {
  hourly: ['Hourly values are not included in this replay.', 'The saved example contains window totals. They cannot be divided into hourly measurements without the original series. In the connected product, this question would request the source series.'],
  sources: ['These sources are not independent confirmations.', 'Open-Meteo best-match may use GFS upstream. The recorded totals differ, but this replay does not contain enough run and model-selection information to explain why. Source agreement alone would not establish accuracy.'],
  missing: ['This preview has one captured weather comparison.', 'Your question has not been sent to the WeatherGPT engine. Use the saved example to explore the interaction, or open the connected app for a live question.'],
};
function Mark({ working = false, large = false }) {
  const reduce = useReducedMotion();
  return <motion.img className={`mark ${large ? 'large' : ''}`} src="/assets/meridian-mark.png" alt="" aria-hidden="true"
    animate={working && !reduce ? { rotate: [0, 14, -8, 0], scale: [1, 1.08, 1] } : { rotate: 0, scale: 1 }}
    transition={working ? { duration: 3.2, repeat: Infinity, ease: 'easeInOut' } : { duration: .35 }} />;
}
function IconButton({ label, children, className = '', ...props }) {
  return <motion.button type="button" whileTap={{ scale: .94 }} className={`icon-button ${className}`} aria-label={label} title={label} {...props}>{children}<span className="tip" aria-hidden="true">{label}</span></motion.button>;
}
export function App() {
  const reduce = useReducedMotion();
  const [calm, setCalm] = useState(false);
  const [visible, setVisible] = useState(!document.hidden);
  const [focused, setFocused] = useState(false);
  const [phase, setPhase] = useState('answer');
  const [stage, setStage] = useState(0);
  const [draft, setDraft] = useState('');
  const [question, setQuestion] = useState(QUESTION);
  const [selected, setSelected] = useState('S62');
  const [inspecting, setInspecting] = useState(false);
  const [followup, setFollowup] = useState(null);
  const [followQuestion, setFollowQuestion] = useState('');
  const [copied, setCopied] = useState(false);
  const [dialog, setDialog] = useState('');
  const [elapsed, setElapsed] = useState(0);
  const input = useRef(null), modal = useRef(null), bottom = useRef(null);
  const timers = useRef([]), copyTimer = useRef(null), composing = useRef(false), sessionQuestion = useRef('');
  const busy = phase === 'working';
  const moving = !reduce && !calm && visible;
  const source = SOURCES.find(item => item.id === selected);
  const clearTimers = () => { timers.current.forEach(clearTimeout); timers.current = []; };
  useEffect(() => {
    const onVisibility = () => setVisible(!document.hidden);
    document.addEventListener('visibilitychange', onVisibility);
    return () => { document.removeEventListener('visibilitychange', onVisibility); clearTimers(); clearTimeout(copyTimer.current); };
  }, []);
  useEffect(() => {
    if (!busy) return;
    const start = Date.now();
    const tick = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 500);
    return () => clearInterval(tick);
  }, [busy]);
  useEffect(() => { if (input.current) { input.current.style.height = 'auto'; input.current.style.height = `${Math.min(input.current.scrollHeight, 138)}px`; } }, [draft]);
  useEffect(() => { if (dialog) modal.current?.showModal(); else modal.current?.close(); }, [dialog]);
  useEffect(() => { if (followup) bottom.current?.scrollIntoView({ behavior: reduce ? 'instant' : 'smooth', block: 'end' }); }, [followup, reduce]);
  function newConversation() {
    clearTimers(); setPhase('welcome'); setDraft(''); setFollowup(null); setInspecting(false); setQuestion(QUESTION); setDialog('');
    requestAnimationFrame(() => input.current?.focus());
  }
  function replay(value = QUESTION) {
    clearTimers(); sessionQuestion.current = value;
    setQuestion(value); setDraft(''); setFollowup(null); setInspecting(false); setStage(0); setElapsed(0); setPhase('working');
    // Timed interaction replay; these labels are not live engine or network events.
    timers.current = [setTimeout(() => setStage(1), 1300), setTimeout(() => setStage(2), 2800), setTimeout(() => { setPhase('answer'); setSelected('S62'); }, 4200)];
  }
  function stop() { clearTimers(); setPhase('cancelled'); setDraft(sessionQuestion.current); requestAnimationFrame(() => input.current?.focus()); }
  function submit(event) {
    event?.preventDefault(); const value = draft.trim(); if (!value || busy) return;
    if (value.toLowerCase().replace(/[.!?]+$/, '') === QUESTION.toLowerCase().replace(/[.!?]+$/, '')) { replay(value); return; }
    const normalized = value.toLowerCase().replace(/[.!?]+$/, '');
    const type = phase === 'answer' && normalized === 'show the hourly values' ? 'hourly' : phase === 'answer' && normalized === 'why do these sources differ' ? 'sources' : 'missing';
    setDraft(''); setFollowQuestion(value); setFollowup(type); if (phase !== 'answer') setPhase('followup');
  }
  function askHourly() { setFollowQuestion('Show the hourly values.'); setFollowup('hourly'); }
  function openSource(id) { setSelected(id); setInspecting(true); }
  async function copyAnswer() {
    try {
      await navigator.clipboard.writeText(`Example replay — 22 Sep 2026\nForecast rainfall · ${WINDOW}\nSurat / Vadodara — model forecasts for selected points\nOpen-Meteo best-match [S62]: Surat 0.4 mm; Vadodara 0.2 mm.\nGFS [S21]: Surat 0.0 mm; Vadodara 0.0 mm.\nSource agreement does not establish accuracy; best-match may include GFS upstream.`);
      setCopied(true); clearTimeout(copyTimer.current); copyTimer.current = setTimeout(() => setCopied(false), 1800);
    } catch { setDialog('copy'); }
  }
  return <MotionConfig reducedMotion="user" transition={{ type: 'spring', stiffness: 360, damping: 34 }}>
    <div className={`app ${moving ? 'motion-on' : 'motion-off'}`} data-phase={phase} data-focused={focused}>
      <motion.div className="atmosphere" aria-hidden="true"
        animate={moving && !focused ? { x: [0, busy ? -18 : -9, 0], y: [0, busy ? 10 : 5, 0], scale: [1, busy ? 1.055 : 1.02, 1], opacity: [busy ? .86 : .7, busy ? 1 : .9, busy ? .86 : .7] } : { x: 0, y: 0, scale: 1, opacity: .65 }}
        transition={moving && !focused ? { duration: busy ? 8 : 24, repeat: Infinity, ease: 'easeInOut' } : { duration: .65 }}><img src="/assets/atmosphere.png" alt="" /></motion.div>
      <nav className="rail" aria-label="Main navigation">
        <IconButton label="Conversation" className={phase !== 'welcome' ? 'active' : ''} onClick={() => { if (!busy) { setPhase('answer'); setQuestion(QUESTION); setFollowup(null); } }}><MessageSquare /></IconButton>
        <IconButton label="New conversation" onClick={newConversation}><Plus /></IconButton>
        <IconButton label="Conversation history" onClick={() => setDialog('history')}><History /></IconButton>
        <IconButton label="Watch" onClick={() => setDialog('watch')}><Bell /></IconButton><div className="rail-divider" />
        <div className="rail-bottom"><IconButton label="Appearance settings" onClick={() => setDialog('settings')}><Settings2 /></IconButton></div>
      </nav>
      <header className="topbar"><a className="wordmark" href="#" onClick={e => { e.preventDefault(); newConversation(); }}>WeatherGPT</a><span className="header-description">Conversational weather intelligence</span><div className="top-actions"><button className="replay" onClick={() => replay()} disabled={busy}><RotateCcw size={14} /> Replay interaction</button><Mark working={busy && visible} /></div></header>
      <main className="main" id="main-content">
        <div className="replay-label"><span>Example replay</span><span aria-hidden="true">·</span><time dateTime="2026-09-22">22 Sep 2026</time><span className="preview-tag">Design preview</span></div>
        <AnimatePresence mode="wait" initial={false}>
          {phase === 'welcome' ? <motion.section key="welcome" className="welcome" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}><Mark large /><p className="eyebrow">WEATHER, WITH CONTEXT</p><h1>A little clarity.<br />Whatever the weather.</h1><p>Ask about a place and a time.<br />Follow an answer all the way to its source.</p><button className="example-prompt" onClick={() => replay()}><span>Compare rain in Surat and Vadodara</span><ArrowRight size={19} /></button><p className="welcome-note">Explore the captured example. No live retrieval in this preview.</p></motion.section> : <motion.div key="thread" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            {phase !== 'followup' && <div className="question-row"><span className="user-avatar" aria-hidden="true">U</span><p>{question}</p></div>}
            <AnimatePresence mode="wait" initial={false}>
              {busy ? <motion.section key="working" className="working" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }}><div className="assistant-avatar"><Mark working={visible} /></div><div><p className="eyebrow">REPLAYING CAPTURED COMPARISON</p><AnimatePresence mode="wait"><motion.h2 key={stage} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}>{stages[stage]}</motion.h2></AnimatePresence><p className="work-meta">Surat + Vadodara <span>·</span> {elapsed}s <span>·</span> <button onClick={stop}>Stop replay</button></p><div className="work-steps" aria-hidden="true">{stages.map((_, i) => <motion.span key={i} animate={{ opacity: i <= stage ? 1 : .22, scaleX: i === stage && moving ? [0.8, 1, .8] : 1 }} transition={{ duration: 1.6, repeat: i === stage && moving ? Infinity : 0 }} />)}</div><p className="simulation-note">A timed preview of the interface, using saved evidence.</p></div></motion.section>
              : phase === 'cancelled' ? <motion.section key="cancelled" className="cancelled" initial={{ opacity: 0 }} animate={{ opacity: 1 }}><Mark /><div><h2>Replay stopped.</h2><p>Your question is back in the composer.</p><button className="text-action" onClick={() => replay(question)}>Try again <ArrowRight size={16} /></button></div></motion.section>
              : phase === 'answer' ? <motion.section key="answer" className="answer-grid" initial={{ opacity: 0, y: 7 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .28, ease: [.22, 1, .36, 1] }}>
                <div className="assistant-avatar"><Mark /></div><article className="answer"><h1>A little more rain in Surat in this forecast.</h1><p className="answer-lead">Open-Meteo best-match gives <strong>0.4 mm</strong> for Surat and <strong>0.2 mm</strong> for Vadodara.</p><p className="validity">Forecast rainfall <span>·</span> {WINDOW}</p><div className="table-scroll"><table><caption className="sr-only">Forecast rainfall totals in millimetres for the selected points and time window.</caption><thead><tr><th scope="col">Forecast product</th><th scope="col">Surat</th><th scope="col">Vadodara</th></tr></thead><tbody>{SOURCES.map(item => <tr key={item.id} className={selected === item.id ? 'selected-row' : ''}><th scope="row"><button onClick={() => openSource(item.id)} aria-expanded={inspecting && selected === item.id} aria-controls="evidence-detail">{item.name} <span className="source-id">[{item.id}]</span></button></th>{item.values.map((v, i) => <td key={i}><span>{v}</span> <small>mm</small></td>)}</tr>)}</tbody></table></div><p className="qualification">Model forecasts for selected points; source agreement does not establish accuracy.</p><div className="answer-actions"><button className="text-action" onClick={askHourly}>Show the hourly values <ArrowRight size={18} /></button><IconButton label={copied ? 'Copied' : 'Copy answer'} className="copy-answer" onClick={copyAnswer}>{copied ? <Check size={17} /> : <Copy size={17} />}</IconButton></div></article>
                <aside className="evidence" aria-label="Answer evidence"><h2>Evidence</h2><p className="source-count">2 sources</p><div className="source-list">{SOURCES.map(item => <button key={item.id} className={`source-entry ${selected === item.id ? 'selected' : ''}`} onClick={() => openSource(item.id)} aria-expanded={inspecting && selected === item.id} aria-controls="evidence-detail"><span className="source-node" /><span className="source-heading"><b>{item.id}</b><span>{item.name}</span></span><span className="source-description">Model forecast for the selected points and time window.</span></button>)}</div><AnimatePresence initial={false}>{inspecting && <motion.div id="evidence-detail" className="evidence-detail" key={selected} initial={{ opacity: 0, height: 0, y: -5 }} animate={{ opacity: 1, height: 'auto', y: 0 }} exit={{ opacity: 0, height: 0 }} transition={{ duration: .25 }}><div className="detail-top"><span>{source.id} · Source detail</span><IconButton label="Close source detail" onClick={() => setInspecting(false)}><X size={15} /></IconButton></div><p>{source.detail}</p><dl><div><dt>Valid</dt><dd>{WINDOW}</dd></div><div><dt>Captured</dt><dd>22 Sep 2026</dd></div><div><dt>Model run</dt><dd>Not recorded in this replay</dd></div></dl><a href={source.url} target="_blank" rel="noreferrer">Product documentation <ExternalLink size={13} /></a></motion.div>}</AnimatePresence></aside>
              </motion.section> : null}
            </AnimatePresence>
            {followup && <motion.section className="followup" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}><p className="follow-question">{followQuestion}</p><div className="follow-answer"><Mark /><div><h2>{followups[followup][0]}</h2><p>{followups[followup][1]}</p>{followup === 'missing' && <button className="text-action" onClick={() => replay()}>Explore the saved comparison <ArrowRight size={16} /></button>}</div></div></motion.section>}
            <div ref={bottom} className="thread-bottom" />
          </motion.div>}
        </AnimatePresence>
      </main>
      <motion.form className={`composer ${focused ? 'is-focused' : ''} ${busy ? 'is-working' : ''}`} onSubmit={submit} layout="position"><div className="composer-context"><MapPin size={17} /><span>{phase === 'welcome' ? 'Name a place in your question' : 'Surat · Vadodara'}</span><button type="button" className="language" onClick={() => setDialog('language')}>English <ChevronDown size={14} /></button></div><div className="composer-input"><IconButton label="Voice input" onClick={() => setDialog('voice')}><Mic size={22} /></IconButton><textarea ref={input} value={draft} rows={1} aria-label="Ask WeatherGPT" placeholder={busy ? 'Preparing the captured comparison…' : 'Ask about a place and a time…'} onChange={e => { setDraft(e.target.value); e.target.style.height = 'auto'; e.target.style.height = `${Math.min(e.target.scrollHeight, 138)}px`; }} onFocus={() => setFocused(true)} onBlur={() => setFocused(false)} onCompositionStart={() => { composing.current = true; }} onCompositionEnd={() => { composing.current = false; }} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing && !composing.current) { e.preventDefault(); submit(); } }} /><motion.button whileTap={{ scale: .92 }} type={busy ? 'button' : 'submit'} className="send" onClick={busy ? stop : undefined} aria-label={busy ? 'Stop replay' : 'Send question'} disabled={!busy && !draft.trim()}><AnimatePresence mode="wait" initial={false}><motion.span key={busy ? 'stop' : 'send'} initial={{ opacity: 0, rotate: -35, scale: .7 }} animate={{ opacity: 1, rotate: 0, scale: 1 }} exit={{ opacity: 0, scale: .7 }} transition={{ duration: .12 }}>{busy ? <Square size={17} fill="currentColor" /> : <ArrowUp size={23} />}</motion.span></AnimatePresence></motion.button></div></motion.form>
      <div className="sr-only" role="status" aria-live="polite">{busy ? `Replay: ${stages[stage]}` : phase === 'cancelled' ? 'Replay stopped. Question restored.' : copied ? 'Answer copied.' : ''}</div>
      <dialog ref={modal} className="dialog" onClose={() => setDialog('')} onClick={e => { if (e.target === e.currentTarget) setDialog(''); }}><div className="dialog-header"><h2>{({ history: 'Your conversations', watch: 'Keep an eye on a place', settings: 'Make room to think', language: 'Answer language', voice: 'Voice input', copy: 'Copy unavailable' })[dialog]}</h2><IconButton label="Close dialog" onClick={() => setDialog('')}><X size={19} /></IconButton></div>
        {dialog === 'history' && <><p className="muted">One captured conversation in this preview.</p><button className="history-entry" onClick={() => { clearTimers(); setPhase('answer'); setQuestion(QUESTION); setFollowup(null); setDialog(''); }}><MessageSquare size={19} /><span>Surat and Vadodara rainfall<small>22 Sep 2026 · Example replay</small></span><ArrowRight size={17} /></button></>}
        {dialog === 'settings' && <><p className="muted">Light, movement, and a steady place to read.</p><div className="setting-row"><div><b>Atmosphere</b><p>Gentle movement at the edge of the page.</p></div><button className="toggle" role="switch" aria-checked={!calm} aria-label="Animated atmosphere" onClick={() => setCalm(v => !v)}>{calm ? <Pause size={15} /> : <Play size={15} />}<span>{calm ? 'Still' : 'On'}</span></button></div><p className="small-note">{reduce ? 'Your system’s reduced-motion preference is active.' : 'System reduced-motion preferences are always respected.'}</p></>}
        {dialog === 'watch' && <><p>A watch keeps a place and a question together.</p><p className="muted">Watch creation and notification delivery are not connected in this design preview. Nothing will be subscribed or sent.</p><button className="dialog-primary" onClick={() => { setDialog(''); setDraft('Keep me posted about rain in Surat.'); input.current?.focus(); }}>Draft a watch question <ArrowRight size={16} /></button></>}
        {dialog === 'language' && <><p className="selected-language">English <Check size={17} /></p><p className="muted">This saved comparison is in English. Other answer languages require the connected product’s verified language path.</p></>}
        {dialog === 'voice' && <><p className="muted">Microphone capture is not connected in this design preview. No audio is recorded or sent. You can type in the composer.</p><button className="dialog-primary" onClick={() => { setDialog(''); input.current?.focus(); }}>Continue with text <ArrowRight size={16} /></button></>}
        {dialog === 'copy' && <p className="muted">The browser did not allow clipboard access. Select the answer text to copy it manually.</p>}
      </dialog>
    </div>
  </MotionConfig>;
}
