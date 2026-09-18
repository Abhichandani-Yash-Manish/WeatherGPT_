import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../test/msw';
import { FrontDoor } from './FrontDoor';

/* The front door states today's published picture and nothing else. These checks pin the three ways it
   can lie: leading with a severity that is not today's, printing a number the read did not state, and
   staying silent when the read failed. The reads go through src/api/client.ts unchanged and msw answers
   the same envelope the engine serves. */

function overview(national: Record<string, unknown>, status = 'ok') {
  return {
    schema_version: 'product-view-v1',
    view: 'overview',
    status,
    generated_at_utc: '2026-09-18T11:18:45.911045+00:00',
    data: { national, radar: { stations: 39, reported: 39 }, places: [] },
    sources: [],
  };
}

function serve(body: Parameters<typeof HttpResponse.json>[0], status = 200) {
  server.use(http.get('/api/overview', () => HttpResponse.json(body, { status })));
}

function renderDoor(onAsk: (question: string) => void = () => {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <FrontDoor onAsk={onAsk} onEnter={() => {}} />
    </QueryClientProvider>,
  );
}

const QUIET_DAY = {
  districts: 756,
  today: { counts: { yellow: 298, green: 445 }, districts_with_no_day_covering_today: 5 },
  bulletin_date: '2026-09-15',
  newest_bulletin_date_in_this_read: '2026-09-15',
  districts_behind_the_newest_edition: 14,
};

describe('the front door', () => {
  it('leads with today\'s own column, not a severity that is already past', async () => {
    /* The live read on 18 September carried one red and 26 orange district-days in the five-day tally
       and every one of them was in the past. A front door that reached for those would announce a
       hazard that is over, so it reads the today block and says plainly that none is in force. */
    serve(overview(QUIET_DAY));
    renderDoor();
    await waitFor(() =>
      expect(screen.getByText(/No district is under an orange or red warning today/i)).toBeInTheDocument(),
    );
    expect(screen.getByText('298')).toBeInTheDocument();
    expect(screen.getByText('445')).toBeInTheDocument();
  });

  it('leads with the hazard when today does carry one', async () => {
    serve(overview({ ...QUIET_DAY, today: { counts: { orange: 3, yellow: 120 }, districts_with_no_day_covering_today: 0 } }));
    renderDoor();
    await waitFor(() =>
      expect(screen.getByText(/districts are under an orange or red warning today/i)).toBeInTheDocument(),
    );
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('names the edition it read and when it read it', async () => {
    serve(overview(QUIET_DAY));
    renderDoor();
    await waitFor(() => expect(screen.getByText(/15 Sep edition/)).toBeInTheDocument());
    expect(screen.getByText(/756 districts/)).toBeInTheDocument();
  });

  it('says which districts are still on an older edition rather than folding them in', async () => {
    serve(overview(QUIET_DAY));
    renderDoor();
    await waitFor(() => expect(screen.getByText(/still publishing an older edition/i)).toBeInTheDocument());
    expect(screen.getByText('14')).toBeInTheDocument();
  });

  it('does not print zero when the read states no today block at all', async () => {
    /* A server that has not been restarted since the today block was added answers without it. Zero
       districts under a caution is a reading; an absent field is not, and the two must not look alike. */
    const { today, ...withoutToday } = QUIET_DAY;
    void today;
    serve(overview(withoutToday));
    renderDoor();
    await waitFor(() =>
      expect(screen.getByText(/did not state the day covering today/i)).toBeInTheDocument(),
    );
    expect(screen.queryByText('0')).not.toBeInTheDocument();
    expect(screen.queryByText(/carry a yellow caution/i)).not.toBeInTheDocument();
    /* The edition line belongs to a stated reading, so it does not appear either. */
    expect(screen.queryByText(/15 Sep edition/)).not.toBeInTheDocument();
  });

  it('states nothing about today when the read fails', async () => {
    serve({ error: 'unavailable' }, 503);
    renderDoor();
    await waitFor(() =>
      expect(screen.getByText(/did not answer this read, so this page states nothing about today/i)).toBeInTheDocument(),
    );
    expect(screen.queryByText(/under an orange or red warning today/i)).not.toBeInTheDocument();
  });

  it('hands the typed question to the conversation', async () => {
    serve(overview(QUIET_DAY));
    const asked: string[] = [];
    renderDoor(question => asked.push(question));
    const box = screen.getByPlaceholderText(/Will it rain in Surat tomorrow morning/i);
    await userEvent.type(box, 'Is any warning in force for Patna today?{Enter}');
    await waitFor(() => expect(asked).toEqual(['Is any warning in force for Patna today?']));
  });

  it('will not ask an empty question', async () => {
    serve(overview(QUIET_DAY));
    const asked: string[] = [];
    renderDoor(question => asked.push(question));
    expect(screen.getByRole('button', { name: 'Ask' })).toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }));
    expect(asked).toEqual([]);
  });
});
