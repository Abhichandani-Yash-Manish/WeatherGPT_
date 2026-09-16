/* Parity checks for the voice component suite tests/test_voice_ui.js. That file prints three checks; two are
   already held by src/chat/chat.test.tsx (only measured writable languages are offered, and a written language
   without verified speech is not speakable). This file holds the remaining one:

   - check 2  a transcript is shown for correction, labelled with the recogniser's own confidence as
              recognition only, and confirmable.

   The recorded transcribe payload below is copied verbatim from the vanilla suite. The React composer shows
   the heard text and the recognition-only label, and takes the text into the question box on request; unlike
   the vanilla panel it does not print the detected language code or the numeric probability from that payload,
   so those two assertions of the vanilla check are reported rather than asserted.

   The microphone is the one stub this file supplies: jsdom has no MediaRecorder, and the vanilla harness
   likewise drove the panel without a real recording. Everything else (the composer, the transcribe route and
   its payload) is the real component and the real transport. */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { Composer } from './Composer';
import type { Languages } from '../api/types';

/* The vanilla constant, verbatim; the React Languages contract also requires the version the route serves. */
const LANGUAGES: Languages = {
  schema_version: 'language-support-view-v1',
  service_configured: true,
  languages: [
    { code: 'en', english_name: 'English', native_name: 'English', measured: { write: 'verified', speak: 'verified' } },
    { code: 'hi', english_name: 'Hindi', native_name: 'हिन्दी', measured: { write: 'verified', speak: 'verified' } },
    { code: 'gu', english_name: 'Gujarati', native_name: 'ગુજરાતી', measured: { write: 'verified', speak: 'unmeasured' } },
    { code: 'ta', english_name: 'Tamil', native_name: 'தமிழ்', measured: { write: 'failed', speak: 'unmeasured' } },
  ],
};

const HEARD = {
  transcript: 'कल अहमदाबाद में 35 मिलीमीटर बारिश होगी',
  detected_language_code: 'hi-IN',
  recognition_probability: 0.83,
};

afterEach(() => {
  vi.unstubAllGlobals();
  Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: undefined });
});

describe('the heard transcript', () => {
  it('shows the transcript for correction, labels recognition confidence as recognition only, and puts the heard text in the question box', async () => {
    class FakeMediaRecorder {
      ondataavailable: ((event: { data: Blob }) => void) | null = null;
      onstop: (() => void) | null = null;
      mimeType = 'audio/webm';
      start() {
        setTimeout(() => this.ondataavailable?.({ data: new Blob(['audio']) }), 0);
      }
      stop() {
        this.onstop?.();
      }
    }
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia: vi.fn(async () => ({ getTracks: () => [] })) },
    });
    vi.stubGlobal('MediaRecorder', FakeMediaRecorder);

    const asked: unknown[] = [];
    server.use(
      http.post('/api/speech/transcribe', async ({ request }) => {
        asked.push(await request.json());
        return HttpResponse.json(HEARD);
      }),
    );

    const onDraft = vi.fn();
    render(<Composer draft="" onDraft={onDraft} onSend={() => {}} busy={false} language="hi" languages={LANGUAGES} />);

    await userEvent.click(screen.getByTestId('record-question'));
    await waitFor(() => expect(screen.getByTestId('record-question')).toHaveTextContent('Stop recording'));
    await userEvent.click(screen.getByTestId('record-question'));

    const panel = await screen.findByTestId('transcript-panel');
    expect(screen.getByTestId('transcript-heard')).toHaveTextContent(HEARD.transcript);
    expect(panel).toHaveTextContent(/Recognition confidence is the recogniser’s own number about its hearing, and is not any answer confidence/);
    expect(panel).toHaveTextContent(/The transcript is a proposal: correct it before asking/);
    expect(asked).toHaveLength(1);

    await userEvent.click(screen.getByRole('button', { name: 'Use this text' }));
    expect(onDraft).toHaveBeenCalledWith(HEARD.transcript);
    expect(screen.queryByTestId('transcript-panel')).toBeNull();
  });
});
