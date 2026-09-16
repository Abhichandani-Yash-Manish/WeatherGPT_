import { useState } from 'react';
import { MotionConfig } from 'motion/react';
import { Rail } from './shell/Rail';
import { SurfaceHost } from './shell/SurfaceHost';
import { useHashRoute } from './shell/useHashRoute';

/* The shell: rail, route host and the chat-first landing surface. R1 shows the frame and the registry;
   R2 fills the Ask surface with the transcript, the reading line and the evidence card. */
export function App() {
  const { view, open } = useHashRoute();
  const [question, setQuestion] = useState('');

  return (
    <MotionConfig reducedMotion="user">
      <div className="flex h-full min-h-screen" data-shell="react" data-surface={view.id}>
        <Rail active={view.id} onOpen={open} />
        <main className="flex min-w-0 flex-1 flex-col">
          <header className="border-b border-line px-6 py-3">
            <h1 className="text-sm font-semibold tracking-wide">WeatherGPT</h1>
            <p className="text-xs text-ink-soft">
              Chat-first workspace. Ask is the front door; every other surface is a module the conversation
              can open.
            </p>
          </header>
          {view.id === 'assistant' ? (
            <section className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center gap-4 px-6 py-10" data-surface="assistant">
              <form
                className="flex items-end gap-2 rounded-card border border-line bg-paper p-3"
                onSubmit={event => event.preventDefault()}
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
              <p className="text-xs text-mute" data-testid="r1-note">
                R1 shell: the rail, the routes and the registry are in place. The transcript, the reading line
                and the evidence card arrive in R2; answers are not wired yet.
              </p>
            </section>
          ) : (
            <SurfaceHost view={view} />
          )}
        </main>
      </div>
    </MotionConfig>
  );
}
