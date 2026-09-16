/* The composer: the one control the whole product turns on. It keeps the question editable, states what
   sending does, and offers voice only where this project has measured the language. */

import { useEffect, useRef, useState } from 'react';
import type { Languages } from '../api/types';
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
      setHeard({
        text,
        detail:
          'Recognition confidence is the recogniser’s own number about its hearing, and is not any answer confidence. ' +
          'The transcript is a proposal: correct it before asking.',
      });
    } catch (error) {
      setVoiceNote(String((error as Error)?.message || error));
    }
  };

  return (
    <div className="composer-shell px-3 py-2" data-busy={busy ? 'true' : 'false'}>
      {heard ? (
        <div className="card mb-2 px-3 py-2" data-testid="transcript-panel">
          <p className="eyebrow">Heard, for correction</p>
          <p className="reading mt-1" data-testid="transcript-heard">{heard.text}</p>
          <p className="mt-1 text-[11px] quiet">{heard.detail}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => {
                onDraft(heard.text);
                setHeard(null);
                box.current?.focus();
              }}
            >
              Use this text
            </button>
            <button type="button" className="btn" onClick={() => setHeard(null)}>Discard it</button>
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
          className="min-h-11 flex-1 bg-transparent text-step-0 outline-none"
          aria-describedby="composer-hint"
        />
        <div className="flex flex-col items-stretch gap-1">
          {busy ? (
            <button type="button" className="btn" onClick={onStop}>Stop</button>
          ) : (
            <button type="button" className="btn btn-primary" onClick={submit} disabled={!draft.trim()} data-testid="send-question">
              Ask
            </button>
          )}
          <button
            type="button"
            className="btn btn-ghost"
            aria-pressed={recording}
            title={canSpeak ? 'Record a question' : 'Speech in this language has not been measured by this project'}
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
          </button>
        </div>
      </div>

      <div id="composer-hint" className="mt-1 flex flex-wrap items-center justify-between gap-2 text-[11px] quiet">
        <span>
          Questions and answers stay on this machine. Ctrl/\u2318 + Enter sends; every value keeps its source and
          retrieval time.
        </span>
        {voiceNote ? <span role="status">{voiceNote}</span> : null}
      </div>
    </div>
  );
}
