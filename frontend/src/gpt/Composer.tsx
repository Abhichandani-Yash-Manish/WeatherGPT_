/* The composer.
   ============================================================================
   ChatGPT's: a rounded panel, a textarea that grows to a ceiling, a row of quiet tools, and one filled round
   send that becomes a stop while a turn is running. Enter sends, Shift+Enter makes a line. Voice is a tool in
   the row rather than a second door, and it confirms what it heard before anything is sent. */

import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ArrowUp, Check, ChevronDown, MapPin, Mic, Square, X } from 'lucide-react';
import { transcribe } from '../chat/api';
import { blobToBase64, startRecording, type Recorder } from '../chat/voice';
import { shortPlace } from '../lib/locale';

export type ComposerProps = {
  draft: string;
  onDraft: (text: string) => void;
  onSend: (text: string) => void;
  onStop: () => void;
  busy: boolean;
  language: string;
  placeholder?: string;
  place?: string | null;
  onContext?: () => void;
  /** Open the place picker. The place control used to call `onContext`, which opened the reading panel -
      a side panel about sources - so the one control labelled "Set a place" did not set a place. */
  onPlace?: () => void;
  /** Set the answer language. The language control used to call `onContext` too, while wearing a chevron
      that promises a menu; it now opens one. */
  onLanguage?: (code: string) => void;
  /** The languages the server says it can answer in, newest read first. */
  languages?: { code: string; label: string }[];
};

export function Composer({
  draft, onDraft, onSend, onStop, busy, language, placeholder, place, onContext, onPlace, onLanguage, languages,
}: ComposerProps) {
  const [pickingLanguage, setPickingLanguage] = useState(false);
  const { t } = useTranslation();
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
      /* The field the route actually answers with. This read `result.text`, and the recogniser returns
         `transcript`: every recording that transcribed perfectly was reported to the reader as "did not
         transcribe into any text", which is a sentence about the product's failure invented by the interface.
         Both names are accepted because the type has always carried both; the order is the route's. */
      const heardText = result.transcript || result.text || '';
      if (!heardText) {
        setNote(result.detail || 'The recording did not transcribe into any text.');
        return;
      }
      /* The recogniser's own report about its hearing, shown as it returned it: which language it thinks it
         heard, and how confident it is about that hearing. Recognition confidence is the model's own number
         about a transcript — it is never answer confidence, never a forecast, and never confidence in a value.
         The sentence is built from the payload's own fields, so a recogniser that stated neither is shown as
         having stated neither. */
      const heardLanguage = result.detected_language_code
        ? 'Heard as ' + result.detected_language_code
        : 'Language as heard not recorded';
      const confidence = typeof result.recognition_probability === 'number'
        ? 'recognition confidence ' + result.recognition_probability
        : 'recognition confidence not recorded';
      setHeard({
        text: heardText,
        detail: heardLanguage + ' · ' + confidence +
          ' — the recogniser’s own number about its hearing, and not any answer confidence, not a forecast and not any kind of' +
          ' confidence in a value. The transcript is a proposal: correct it before asking.',
      });
    } catch (error) {
      setNote(String((error as Error)?.message || error));
    }
  };

  return (
    <div className="g-composer">
      {/* What the microphone heard, for correction. Nothing is sent until the reader accepts it. */}
      {heard ? (
        <div className="g-heard" data-testid="transcript-panel">
          <p className="g-heard-head"><Mic size={13} aria-hidden="true" /> {t('composer.heard')}</p>
          <p className="g-heard-text" data-testid="transcript-heard">{heard.text}</p>
          <p className="g-claim-source">{heard.detail}</p>
          <div className="g-chips">
            <button type="button" className="g-chip" onClick={() => { onDraft(heard.text); setHeard(null); box.current?.focus(); }}>
              <Check size={13} aria-hidden="true" /> {t('composer.useText')}
            </button>
            <button type="button" className="g-chip" onClick={() => setHeard(null)}>
              <X size={13} aria-hidden="true" /> {t('composer.discard')}
            </button>
          </div>
        </div>
      ) : null}

      <label className="sr-only" htmlFor="question">{t('composer.label')}</label>
      <textarea
        id="question"
        ref={box}
        rows={1}
        value={draft}
        maxLength={1500}
        placeholder={placeholder || t('composer.placeholder')}
        onChange={event => onDraft(event.target.value)}
        onKeyDown={event => {
          if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing && event.keyCode !== 229) {
            event.preventDefault();
            submit();
          }
        }}
        aria-describedby="composer-hint"
      />

      <div className="g-composer-row">
      {/* THE TWO CONTROLS THAT SAY WHAT THIS ANSWER WILL BE ABOUT, and both of them now do what they say.
            Until this batch they called one handler between them, which opened the reading panel: pressing
            "Set a place" opened a list of sources, and pressing a control wearing a dropdown chevron opened
            the same panel rather than a menu. A control that does not do the thing on its label is worse
            than no control, because a reader stops trusting the rest of them. */}
        {onContext ? <div className="g-composer-context">
          <button
            type="button"
            onClick={() => (onPlace ? onPlace() : onContext())}
            title={place ? 'Change the place this conversation is about — ' + place : 'Choose the place this conversation is about'}
          >
            <MapPin size={14} aria-hidden="true" />
            <span>{place ? shortPlace(place) : 'Set a place'}</span>
          </button>
          <div className="g-composer-language">
            <button
              type="button"
              onClick={() => setPickingLanguage(open => !open)}
              aria-expanded={pickingLanguage}
              aria-haspopup="menu"
              title="Choose the language answers are written in"
            >
              {/* Short by design: this sits in a row with the place, the microphone and the send, and the
                full name of the option belongs in the menu rather than on the control that opens it. */}
            <span>{languages?.find(entry => entry.code === language)?.label || (language ? language : 'Auto')}</span>
              <ChevronDown size={13} aria-hidden="true" />
            </button>
            {pickingLanguage && onLanguage ? (
              <ul className="g-menu g-language-menu" role="menu" aria-label="Answer language">
                {[{ code: '', label: 'Auto — match the question' }, ...(languages || [])].map(entry => (
                  <li key={entry.code || 'auto'}>
                    <button
                      type="button"
                      role="menuitemradio"
                      aria-checked={(language || '') === entry.code}
                      onClick={() => { onLanguage(entry.code); setPickingLanguage(false); }}
                    >
                      {entry.label}
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </div> : null}
        <button
          type="button"
          className="g-tool"
          data-testid="record-question"
          aria-pressed={recording}
          aria-label={recording ? t('composer.stopRecording') : t('composer.record')}
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
          <button type="button" className="g-send" onClick={onStop} aria-label={t('composer.stop')} data-testid="stop-turn">
            <Square size={14} aria-hidden="true" />
          </button>
        ) : (
          <button type="button" className="g-send" onClick={submit} disabled={!draft.trim()} aria-label={t('composer.send')} data-testid="send-question">
            <ArrowUp size={17} aria-hidden="true" />
          </button>
        )}
      </div>
    </div>
  );
}
