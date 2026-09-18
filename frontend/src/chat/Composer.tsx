/* The composer: the one control the whole product turns on. It keeps the question editable, states what
   sending does, and offers voice only where this project has measured the language. */

import { useEffect, useRef, useState } from 'react';
import { ArrowUp, Check, Keyboard, Mic, MicOff, Square, X } from 'lucide-react';
import type { Languages } from '../api/types';
import { Button } from '../ui/kit';
import { transcribe } from './api';
import { blobToBase64, findLanguage, isSpeakable, startRecording, type Recorder } from './voice';

export type ComposerProps = {
  draft: string;
  onDraft: (text: string) => void;
  onSend: (text: string) => void;
  busy: boolean;
  language: string;
  languages?: Languages;
  onStop?: () => void;
};

export function Composer({ draft, onDraft, onSend, busy, language, languages, onStop }: ComposerProps) {
  const box = useRef<HTMLTextAreaElement | null>(null);
  const recorder = useRef<Recorder | null>(null);
  const [recording, setRecording] = useState(false);
  const [voiceNote, setVoiceNote] = useState('');
  const [heard, setHeard] = useState<{ text: string; detail: string } | null>(null);

  useEffect(() => {
    if (box.current && !busy) box.current.focus();
  }, [busy]);

  useEffect(() => () => recorder.current?.cancel(), []);

  const spokenLanguage = findLanguage(languages, language) || findLanguage(languages, 'en');
  const canSpeak = isSpeakable(spokenLanguage);

  const submit = () => {
    const text = draft.trim();
    if (!text || busy) return;
    onSend(text);
  };

  const stopRecording = async () => {
    const active = recorder.current;
    if (!active) return;
    recorder.current = null;
    setRecording(false);
    try {
      const { blob, contentType } = await active.stop();
      setVoiceNote('Transcribing the recording…');
      const encoded = await blobToBase64(blob);
      const result = await transcribe({ audio_base64: encoded, content_type: contentType, language: language || undefined });
      const text = result.transcript || result.text || '';
      if (!text) {
        setVoiceNote(result.detail || 'The recording did not transcribe into any text.');
        return;
      }
      setVoiceNote('');
      /* The recogniser's own report about its hearing is shown as it returned it: which language it thinks it
         heard, and how confident it is about that hearing. Recognition confidence is never answer confidence. */
      const heardLanguage = result.detected_language_code ? 'Heard as ' + result.detected_language_code : 'Language as heard not recorded';
      const confidence = typeof result.recognition_probability === 'number'
        ? 'recognition confidence ' + result.recognition_probability
        : 'recognition confidence not recorded';
      setHeard({
        text,
        detail:
          heardLanguage + ' · ' + confidence +
          " — the recogniser’s own number about its hearing, and not any answer confidence, not a forecast and not any kind of" +
          ' confidence in a value. The transcript is a proposal: correct it before asking.',
      });
    } catch (error) {
      setVoiceNote(String((error as Error)?.message || error));
    }
  };

  return (
    <div className="composer-shell glass-strong px-3 py-2.5" data-busy={busy ? 'true' : 'false'}>
      {heard ? (
        <div className="glass-strong pop-in mb-2 p-3" data-testid="transcript-panel">
          <p className="eyebrow flex items-center gap-2"><Mic size={14} aria-hidden="true" />Heard, for correction</p>
          <p className="reading mt-1" data-testid="transcript-heard">{heard.text}</p>
          <p className="mt-1 text-[11px] quiet">{heard.detail}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button
              variant="primary"
              icon={<Check size={14} />}
              onClick={() => {
                onDraft(heard.text);
                setHeard(null);
                box.current?.focus();
              }}
            >
              Use this text
            </Button>
            <Button icon={<X size={14} />} onClick={() => setHeard(null)}>Discard it</Button>
          </div>
        </div>
      ) : null}

      <label className="sr-only" htmlFor="question">Your question</label>
      <div className="flex items-end gap-2">
        <textarea
          id="question"
          ref={box}
          value={draft}
          rows={2}
          maxLength={1500}
          onChange={event => onDraft(event.target.value)}
          onKeyDown={event => {
            if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
              event.preventDefault();
              submit();
            }
          }}
          placeholder="What is it like right now in Ahmedabad?"
          className="min-h-11 flex-1 resize-none bg-transparent px-1 py-2 text-step-0 text-ink outline-none placeholder:text-mute"
          aria-describedby="composer-hint"
        />
        <div className="flex items-center gap-1.5 pb-0.5">
          {busy ? (
            <Button icon={<Square size={14} />} onClick={onStop}>Stop</Button>
          ) : (
            <Button
              variant="primary"
              size="lg"
              icon={<ArrowUp size={16} />}
              onClick={submit}
              disabled={!draft.trim()}
              data-testid="send-question"
            >
              Ask
            </Button>
          )}
          {/* The recording control keeps a written label: an icon alone cannot say which of two states
              a control that captures a voice is in. */}
          <Button
            icon={recording ? <MicOff size={16} /> : <Mic size={16} />}
            aria-pressed={recording}
            tip={canSpeak ? 'Record a question' : 'Speech in this language has not been measured by this project'}
            className={recording ? 'text-alert' : undefined}
            onClick={() => {
              if (recording) void stopRecording();
              else {
                setHeard(null);
                setVoiceNote('');
                startRecording()
                  .then(active => {
                    recorder.current = active;
                    setRecording(true);
                  })
                  .catch(error => setVoiceNote(String((error as Error)?.message || error)));
              }
            }}
            data-testid="record-question"
          >
            {recording ? 'Stop recording' : 'Speak'}
          </Button>
        </div>
      </div>

      <div id="composer-hint" className="mt-1.5 flex flex-wrap items-center justify-between gap-2 text-[11px] quiet">
        <span className="flex items-center gap-1.5">
          <Keyboard size={13} aria-hidden="true" />
          Questions and answers stay on this machine. Ctrl/⌘ + Enter sends; every value keeps its source and
          retrieval time.
        </span>
        {voiceNote ? <span role="status">{voiceNote}</span> : null}
      </div>
    </div>
  );
}
