/* Voice, with the two rules the recorded checks already hold this project to: only a language whose
   writing this project has measured is offered, and speech is refused rather than guessed where the
   project has not verified it. Recognition confidence is the model's own number about its hearing; it is
   never an answer confidence and never a forecast confidence. */

import type { LanguageEntry, Languages } from '../api/types';

export function measuredFor(language: LanguageEntry | undefined, ability: 'write' | 'hear' | 'speak'): string {
  return String(language?.measured?.[ability] || 'unmeasured');
}

/* The languages a reader may be offered for writing: the ones this project has measured, sorted by name. */
export function writableLanguages(languages?: Languages): LanguageEntry[] {
  const rows = languages?.languages || [];
  return rows
    .filter(language => measuredFor(language, 'write') === 'verified')
    .slice()
    .sort((left, right) => left.english_name.localeCompare(right.english_name));
}

/* Every language the workspace knows about, measured first, so an unmeasured one can be shown as such
   rather than silently missing from the list. */
export function allLanguages(languages?: Languages): LanguageEntry[] {
  const rows = languages?.languages || [];
  return rows.slice().sort((left, right) => {
    const leftMeasured = measuredFor(left, 'write') === 'verified' ? 0 : 1;
    const rightMeasured = measuredFor(right, 'write') === 'verified' ? 0 : 1;
    if (leftMeasured !== rightMeasured) return leftMeasured - rightMeasured;
    return left.english_name.localeCompare(right.english_name);
  });
}

export function isSpeakable(language: LanguageEntry | undefined): boolean {
  return measuredFor(language, 'speak') === 'verified';
}

export function findLanguage(languages: Languages | undefined, code: string): LanguageEntry | undefined {
  return (languages?.languages || []).find(language => language.code === code);
}

export function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('The recording could not be read in this browser.'));
    reader.onload = () => {
      const result = String(reader.result || '');
      const comma = result.indexOf(',');
      resolve(comma >= 0 ? result.slice(comma + 1) : result);
    };
    reader.readAsDataURL(blob);
  });
}

export type Recorder = { stop: () => Promise<{ blob: Blob; contentType: string }>; cancel: () => void };

export async function startRecording(): Promise<Recorder> {
  const devices = navigator.mediaDevices;
  if (!devices?.getUserMedia || typeof MediaRecorder === 'undefined') {
    throw new Error('This browser does not offer microphone recording, so a question cannot be spoken here.');
  }
  const stream = await devices.getUserMedia({ audio: true });
  const recorder = new MediaRecorder(stream);
  const chunks: BlobPart[] = [];
  recorder.ondataavailable = event => {
    if (event.data.size) chunks.push(event.data);
  };
  recorder.start();
  const close = () => stream.getTracks().forEach(track => track.stop());
  return {
    stop: () =>
      new Promise(resolve => {
        recorder.onstop = () => {
          close();
          resolve({ blob: new Blob(chunks, { type: recorder.mimeType || 'audio/webm' }), contentType: recorder.mimeType || 'audio/webm' });
        };
        recorder.stop();
      }),
    cancel: () => {
      try {
        recorder.stop();
      } catch {
        /* already stopped */
      }
      close();
    },
  };
}

/* Play a spoken rendering the server produced. It is a reading of text that was already checked, so the
   interface says exactly that beside the control. */
export function playSegments(segments: string[], codec: string): HTMLAudioElement | null {
  if (!segments.length) return null;
  const type = codec === 'mp3' ? 'audio/mpeg' : codec === 'opus' ? 'audio/ogg' : 'audio/wav';
  const source = 'data:' + type + ';base64,' + segments[0];
  const audio = new Audio(source);
  void audio.play().catch(() => undefined);
  return audio;
}
