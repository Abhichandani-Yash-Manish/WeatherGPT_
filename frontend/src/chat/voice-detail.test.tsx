/* The recogniser's own report, and the honest sentence for a stopped request.

   Two rules the vanilla checks held and the React path did not: a transcript for correction states which language
   the recogniser thinks it heard and the confidence it attaches to that hearing (never an answer confidence), and
   a request the client stopped waiting for says the server may still be finishing it rather than implying it
   stopped. */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { api } from '../api/client';
import { Composer } from '../gpt/Composer';
import { server } from '../test/msw';

function mount(node: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);
}

function recordingStub() {
  const listeners: Record<string, (event: { data?: Blob }) => void> = {};
  class Recorder {
    mimeType = 'audio/webm';
    state = 'recording';
    ondataavailable: ((event: { data: Blob }) => void) | null = null;
    onstop: (() => void) | null = null;
    start() {
      this.ondataavailable?.({ data: new Blob(['heard'], { type: 'audio/webm' }) });
    }
    stop() {
      this.state = 'inactive';
      this.onstop?.();
    }
  }
  Object.defineProperty(window, 'MediaRecorder', { configurable: true, value: Recorder });
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: { getUserMedia: async () => ({ getTracks: () => [{ stop: () => {} }] }) },
  });
  return listeners;
}

describe('the recogniser report and a stopped request', () => {
  it('states the language the recogniser heard and its confidence about that hearing, as recognition only', async () => {
    recordingStub();
    server.use(
      http.post('/api/speech/transcribe', () => HttpResponse.json({
        transcript: 'कल अहमदाबाद में 35 मिलीमीटर बारिश होगी',
        detected_language_code: 'hi-IN',
        recognition_probability: 0.83,
        state: 'transcribed',
      })),
    );
    mount(<Composer draft="" onDraft={() => {}} onSend={() => {}} onStop={() => {}} busy={false} language="hi" />);
    /* The control records until it is pressed again: the first press starts, the second stops and sends the
       recording for transcription. */
    await userEvent.click(screen.getByTestId('record-question'));
    await waitFor(() => expect(screen.getByTestId('record-question')).toHaveAttribute('aria-label', 'Stop recording'));
    await userEvent.click(screen.getByTestId('record-question'));
    await waitFor(() => expect(screen.getByTestId('transcript-panel')).toBeInTheDocument());
    expect(screen.getByTestId('transcript-heard')).toHaveTextContent('कल अहमदाबाद');
    const panel = screen.getByTestId('transcript-panel');
    expect(panel).toHaveTextContent('Heard as hi-IN');
    expect(panel).toHaveTextContent('recognition confidence 0.83');
    expect(panel).toHaveTextContent(/not any answer confidence/i);
    expect(panel).toHaveTextContent(/not a forecast/i);
  });

  it('says the server may still be finishing a request the client stopped waiting for', async () => {
    const controller = new AbortController();
    server.use(
      http.get('/api/coverage-slow', async () => {
        controller.abort();
        await new Promise(resolve => setTimeout(resolve, 20));
        return HttpResponse.json({ ok: true });
      }),
    );
    await expect(api('/api/coverage-slow', {}, { signal: controller.signal })).rejects.toThrow(/may still be finishing it/i);
  });
});
