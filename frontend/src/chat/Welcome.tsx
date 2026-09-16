/* The welcome: what the workspace is for, and five openings that lead with what this build does best.
   The limit paragraph is the same sentence the repository documents, so the first screen cannot promise
   more than the build delivers. */

import type { Persona } from '../api/types';

const OPENINGS: [string, string][] = [
  ['What is it like right now in Ahmedabad?', 'Ask what it is like right now'],
  ['Is any warning in force for Patna, Bihar today?', 'Check today’s published warnings'],
  ['What does the district agromet advisory for Ahmedabad say for cotton?', 'Read the farm advisory'],
  ['Show the annual rainfall trend for Ahmedabad district from 1981 to 2010.', 'Look at a trend'],
  ['What is the current weather at VOBL?', 'Ask for an airport report'],
];

export function Welcome({ onAsk, reading, place }: { onAsk: (question: string) => void; reading?: Persona | null; place?: string }) {
  const named = place || 'Ahmedabad, Gujarat';
  const openings: [string, string][] = OPENINGS.map((pair, index) => (index === 0 ? [pair[0].replace('Ahmedabad', named.split(',')[0]), pair[1]] : pair));
  const starters = reading?.starters?.slice(0, 3).map(question => [question, 'Ask as ' + (reading.label || '').toLowerCase()] as [string, string]) || [];
  const list = [...starters, ...openings].slice(0, 6);

  return (
    <article className="rise mx-auto w-full max-w-3xl px-1 py-6" data-testid="welcome">
      <h1 className="display">Ask about a place and a time.</h1>
      <p className="reading mt-3">
        Ask in your own words and follow up in the same conversation. WeatherGPT resolves the place, retrieves
        the evidence, and keeps the source, the window and the retrieval time attached to every value. When a
        name is shared between places it asks you which one you mean.
      </p>
      {reading ? (
        <p className="mt-2 text-xs text-ink-soft">
          Reading as {reading.label}: {reading.who} {reading.note}
        </p>
      ) : null}
      <div className="starters-grid mt-4">
        {list.map(([question, label]) => (
          <button key={question} type="button" className="btn justify-start text-left" onClick={() => onAsk(question)}>
            {label}
          </button>
        ))}
      </div>
      <p className="mt-4 text-xs quiet">
        It will not invent a warning, an observation, a water level or a forecast, and it says when evidence is
        missing rather than filling the gap. Radar and satellite imagery, official sea-area bulletins and flood
        extent are not connected. Plans and their inbox work only while this local workspace is running.
      </p>
    </article>
  );
}
