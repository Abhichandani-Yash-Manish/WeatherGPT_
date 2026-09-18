/* The composer.
   ============================================================================
   ChatGPT's: a rounded panel, a textarea that grows to a ceiling, a row of quiet tools, and one filled round
   send that becomes a stop while a turn is running. Enter sends, Shift+Enter makes a line. Voice is a tool in
   the row rather than a second door, and it confirms what it heard before anything is sent. */

import { useEffect, useRef, useState } from 'react';
import { ArrowUp, Check, Mic, Square, X } from 'lucide-react';
import { transcribe } from '../chat/api';
import { blobToBase64, startRecording, type Recorder } from '../chat/voice';

export type ComposerProps = {
  draft: string;
  onDraft: (text: string) => void;
  onSend: (text: string) => void;
  onStop: () => void;
  busy: boolean;
  language: string;
  placeholder?: string;
};

export function Composer({ draft, onDraft, onSend, onStop, busy, language, placeholder }: ComposerProps) {
  const box = useRef<HTMLTextAreaElement | null>(null);
  const recorder = useRef<Recorder | null>(null);
  const [recording, setRecording] = useState(false);
  const [heard, setHeard] = useState<{ text: string; detail?: string } | null>(null);
  const [note, setNote] = useState('');

  /* Grow to the ceiling the stylesheet sets, then scroll — the same behaviour the reference has. */
  useEffect(() => {
    const node = box.current;
    if (!node) return;
    node.style.height = 'auto';
    node.style.height = Math.min(node.scrollHeight, 200) + 'px';
  }, [draft]);

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
      const encoded = await blobToBase64(blob);
      const result = await transcribe({ audio_base64: encoded, content_type: contentType, language: language || undefined });
      if (result.text) setHeard({ text: result.text, detail: result.detail });
      else setNote(result.detail || 'The recording did not transcribe into any text.');
    } catch (error) {
      setNote(String((error as Error)?.message || error));
    }
  };

  return (
    <div className="g-composer">
      {/* What the microphone heard, for correction. Nothing is sent until the reader accepts it. */}
      {heard ? (
        <div className="g-notice" style={{ margin: '0 0 6px' }} data-testid="heard">
          <p style={{ margin: 0, fontSize: 13 }}>Heard: “{heard.text}”</p>
          {heard.detail ? <p className="g-claim-source" style={{ marginTop: 4 }}>{heard.detail}</p> : null}
          <div className="g-chips" style={{ marginTop: 8 }}>
            <button type="button" className="g-chip" onClick={() => { onDraft(heard.text); setHeard(null); box.current?.focus(); }}>
              <Check size={13} aria-hidden="true" /> Use it
            </button>
            <button type="button" className="g-chip" onClick={() => setHeard(null)}>
              <X size={13} aria-hidden="true" /> Discard
            </button>
          </div>
        </div>
      ) : null}

      <label className="sr-only" htmlFor="question">Your question</label>
      <textarea
        id="question"
        ref={box}
        rows={1}
        value={draft}
        maxLength={1500}
        placeholder={placeholder || 'Ask about a place and a time…'}
        onChange={event => onDraft(event.target.value)}
        onKeyDown={event => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            submit();
          }
        }}
        aria-describedby="composer-hint"
      />

      <div className="g-composer-row">
        <button
          type="button"
          className="g-tool"
          aria-pressed={recording}
          aria-label={recording ? 'Stop recording' : 'Record a question'}
          onClick={() => {
            if (recording) void stopRecording();
            else {
              setHeard(null);
              setNote('');
              startRecording()
                .then(active => { recorder.current = active; setRecording(true); })
                .catch(error => setNote(String((error as Error)?.message || error)));
            }
          }}
        >
          <Mic size={16} aria-hidden="true" />
          {recording ? 'Stop' : null}
        </button>
        {note ? <span className="g-claim-source" role="status">{note}</span> : null}
        <span className="g-spacer" />
        {busy ? (
          <button type="button" className="g-send" onClick={onStop} aria-label="Stop generating">
            <Square size={14} aria-hidden="true" />
          </button>
        ) : (
          <button type="button" className="g-send" onClick={submit} disabled={!draft.trim()} aria-label="Send" data-testid="send-question">
            <ArrowUp size={17} aria-hidden="true" />
          </button>
        )}
      </div>
    </div>
  );
}
