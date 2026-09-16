import { useState } from 'react';
import { MotionConfig } from 'motion/react';

/* R0 shell: the frame the stages fill in. It renders the chat-first landing surface and states, in the
   interface, that this build is groundwork — the vanilla frontend still serves the product until R6. */
export function App() {
  const [question, setQuestion] = useState('');

  return (
    <MotionConfig reducedMotion="user">
      <div className="flex h-full min-h-screen flex-col" data-surface="assistant">
        <header className="border-b border-line px-6 py-4">
          <h1 className="text-lg font-semibold">WeatherGPT</h1>
          <p className="text-sm text-ink-soft">
            Chat-first workspace. React groundwork build (R0): the conversation is the front door, and every other
            surface becomes a module it can open.
          </p>
        </header>
        <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center gap-4 px-6 py-10">
          <form
            className="flex items-end gap-2 rounded-card border border-line bg-paper p-3"
            onSubmit={event => {
              event.preventDefault();
            }}
          >
            <label className="sr-only" htmlFor="question">
              Your question
            </label>
            <textarea
              id="question"
              value={question}
              onChange={event => setQuestion(event.target.value)}
              rows={2}
              className="min-h-11 flex-1 resize-none bg-transparent text-base outline-none"
              placeholder="What is it like right now in Ahmedabad?"
            />
            <button type="submit" className="rounded-card bg-data px-4 py-2 font-semibold text-paper">
              Ask
            </button>
          </form>
          <p className="text-xs text-mute" data-testid="r0-note">
            Answers are not wired in this build yet: the engine contract, the reading line and the evidence card
            arrive in R1 and R2.
          </p>
        </main>
      </div>
    </MotionConfig>
  );
}
