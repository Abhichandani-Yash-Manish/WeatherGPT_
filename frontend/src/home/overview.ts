/* The national read, described once.
   ============================================================================
   Three surfaces now show the country's published picture — the chat face's opening line, the board's tiles,
   and the older front door's tests — so the description lives in one place and the rules live with it:

   1. An absent `today` block is not a quiet day.
   2. A number that no read stated is never printed; a zero a read stated is printed.
   3. The edition line is only printed where the read stated an edition.
   4. Every count carries the read time. */

import { useQuery } from '@tanstack/react-query';
import { getJson } from '../api/client';
import type { Envelope } from '../api/types';
import { istClock, monthName } from '../lib/time';

export type TodayBlock = { counts?: Record<string, number>; districts_with_no_day_covering_today?: number };
/* The whole of what GET /api/overview answers, in one place: the description below and the Today surface both
   read this payload, and two local shapes for one response is how the same read starts meaning two things. */
export type OverviewData = {
  national?: {
    districts?: number;
    skipped?: number;
    tally?: Record<string, number>;
    today?: TodayBlock;
    bulletin_date?: string | null;
    bulletin_dates?: Record<string, number>;
    newest_bulletin_date_in_this_read?: string | null;
    districts_behind_the_newest_edition?: number | null;
    oldest_bulletin_age_days?: number | null;
  };
  radar?: { stations?: number; reported?: number };
  places?: unknown[];
};

/* The month table moved to lib/time.ts, where the locale lives. This file had its own copy of it plus a
   second hardcoded 'en-GB', which is how one interface ends up formatting in two conventions: the edition
   line and the read clock must state the same month the same way. The day stays unpadded here - an edition
   label reads "5 Sep", not "05 Sep" - so the composition stays local and only the month is shared. */
export function editionLabel(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const parts = String(iso).split('-');
  if (parts.length !== 3) return String(iso);
  const month = monthName(Number(parts[1]));
  return month ? `${Number(parts[2])} ${month}` : String(iso);
}

export function readClock(iso: string | null | undefined): string | null {
  const clock = istClock(iso);
  return clock ? clock + ' IST' : null;
}

export function useOverview() {
  return useQuery({
    queryKey: ['overview', 'national'],
    queryFn: () => getJson<Envelope<OverviewData>>('/api/overview'),
    staleTime: 60_000,
  });
}

export type NationalPicture = {
  statedToday: boolean;
  red: number;
  orange: number;
  yellow: number;
  green: number;
  severe: number;
  districts: number | null;
  behind: number | null;
  noDay: number | null;
  edition: string | null;
  readAt: string | null;
  /** The provenance line, or null when the read has not answered. */
  sourceLine: string | null;
};

export function describeNational(overview: ReturnType<typeof useOverview>): NationalPicture {
  const national = overview.data?.data?.national;
  const counts = national?.today?.counts || {};
  const statedToday = Boolean(national?.today && Object.keys(counts).length > 0);
  const red = counts.red || 0;
  const orange = counts.orange || 0;
  const districts = national?.districts ?? null;
  const edition = editionLabel(national?.newest_bulletin_date_in_this_read || national?.bulletin_date);
  const readAt = readClock(overview.data?.generated_at_utc);
  const sourceLine = [
    'IMD district warning bulletin',
    edition ? `${edition} edition` : 'edition not stated',
    districts !== null ? `${districts} districts` : null,
    readAt ? `read ${readAt}` : null,
  ]
    .filter(Boolean)
    .join(' · ');
  return {
    statedToday,
    red,
    orange,
    yellow: counts.yellow || 0,
    green: counts.green || 0,
    severe: red + orange,
    districts,
    behind: national?.districts_behind_the_newest_edition ?? null,
    noDay: national?.today?.districts_with_no_day_covering_today ?? null,
    edition,
    readAt,
    sourceLine: overview.data ? sourceLine : null,
  };
}
