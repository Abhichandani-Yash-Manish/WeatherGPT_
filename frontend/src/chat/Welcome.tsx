/* The welcome: what the workspace is for, and the openings that lead with what this build does best.
   The limit paragraph is the same sentence the repository documents, so the first screen cannot promise
   more than the build delivers. Each opening carries the idea it belongs to, from one icon map. */

import { motion } from 'motion/react';
import { Sparkles } from 'lucide-react';
import type { Persona } from '../api/types';
import { IDEA_ICONS } from '../ui/icons';

const OPENINGS: [string, string, string][] = [
  ['What is it like right now in Ahmedabad?', 'Ask what it is like right now', 'station'],
  ['Is any warning in force for Patna, Bihar today?', 'Check today’s published warnings', 'warning'],
  ['What does the district agromet advisory for Ahmedabad say for cotton?', 'Read the farm advisory', 'documents'],
  ['Show the annual rainfall trend for Ahmedabad district from 1981 to 2010.', 'Look at a trend', 'chart'],
  ['What is the current weather at VOBL?', 'Ask for an airport report', 'panel'],
];

export function Welcome({ onAsk, reading, place }: { onAsk: (question: string) => void; reading?: Persona | null; place?: string }) {
  const named = place || 'Ahmedabad, Gujarat';
  const openings: [string, string, string][] = OPENINGS.map((entry, index) => (index === 0 ? [entry[0].replace('Ahmedabad', named.split(',')[0]), entry[1], entry[2]] : entry));
  const starters = reading?.starters?.slice(0, 3).map(question => [question, 'Ask as ' + (reading.label || '').toLowerCase(), 'sparkle'] as [string, string, string]) || [];
  const list = [...starters, ...openings].slice(0, 6);

  return (
    <article className="mx-auto w-full max-w-3xl px-1 py-8" data-testid="welcome">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: .4, ease: [0.16, 1, 0.3, 1] }}
      >
        <span className="pill pill-accent mb-3"><Sparkles size={13} aria-hidden="true" />Local workspace · India</span>
        <h1 className="display">Ask about a place and a time.</h1>
        <p className="reading mt-3">
          Ask in your own words and follow up in the same conversation. WeatherGPT resolves the place, retrieves
          the evidence, and keeps the source, the window and the retrieval time attached to every value. When a
          name is shared between places it asks you which one you mean.
        </p>
        {reading ? (
          <p className="mt-2 text-[length:var(--step--1)] text-ink-soft">
            Reading as {reading.label}: {reading.who} {reading.note}
          </p>
        ) : null}
      </motion.div>

      <div className="starters-grid mt-5">
        {list.map(([question, label, idea], index) => {
          const Icon = IDEA_ICONS[idea] ?? Sparkles;
          return (
            <motion.button
              key={question}
              type="button"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: .05 + index * .04, duration: .3, ease: [0.16, 1, 0.3, 1] }}
              className="glass sheen flex items-start gap-3 p-3 text-left transition-transform hover:-translate-y-0.5"
              onClick={() => onAsk(question)}
            >
              <span className="icon-tile shrink-0" aria-hidden="true"><Icon size={16} /></span>
              <span className="min-w-0">
                <span className="block font-semibold text-ink">{label}</span>
                <span className="mt-0.5 block truncate text-[length:var(--step--1)] quiet">{question}</span>
              </span>
            </motion.button>
          );
        })}
      </div>

      <p className="mt-5 text-[length:var(--step--1)] quiet">
        It will not invent a warning, an observation, a water level or a forecast, and it says when evidence is
        missing rather than filling the gap. Radar and satellite imagery, official sea-area bulletins and flood
        extent are not connected. Plans and their inbox work only while this local workspace is running.
      </p>
    </article>
  );
}
