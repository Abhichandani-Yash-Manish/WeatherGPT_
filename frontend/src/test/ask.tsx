/* The conversation, mounted the way the shipped shell mounts it.
   ============================================================================
   The card, the composer and the engine are checked by driving the real surface — the one that ships — rather
   than a page of their own. The surface these specs used to drive was the legacy AskSurface, which is deleted;
   a second chat page kept alive for tests would be a second thing to keep true.

   The shell reads its own furniture on mount (the language catalogue, the persona catalogue, the stored
   conversations). The shared msw server answers all three, so a spec that cares about one of them overrides
   that handler and one that does not is not asked to name it. */

import { render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Workspace } from '../gpt/Workspace';
import type { Seed } from '../App';

export type AskOptions = {
  language?: string;
  persona?: string;
  restoreId?: string | null;
  seed?: Seed;
  onAsk?: (question: string) => void;
};

export function renderAsk(options: AskOptions = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 } } });
  return render(
    <QueryClientProvider client={client}>
      <Workspace
        onOpen={() => {}}
        language={options.language ?? ''}
        onLanguage={() => {}}
        persona={options.persona ?? ''}
        onPersona={() => {}}
        restoreId={options.restoreId ?? null}
        seed={options.seed ?? null}
        onAsk={options.onAsk}
      />
    </QueryClientProvider>,
  );
}
