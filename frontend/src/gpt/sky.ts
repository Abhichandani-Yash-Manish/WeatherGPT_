/* What the sky is doing, when a source says so.
   ============================================================================
   The welcome screen draws a condition glyph and the ground takes its colour from it. That is the one place
   in this product where a drawing could become a weather claim, so this module exists to make the claim
   impossible rather than unlikely.

   The rule: a condition is drawn only when a station report printed one, and it arrives with the station,
   its source id and the time it was read. There is no default and no inference. If the nearest station
   printed no weather field, `condition` is null and the screen shows the hour instead — the hour is
   astronomy, computed from the reader's own latitude, and astronomy is not a forecast.

   What this deliberately does NOT do:
     - guess a condition from temperature, humidity or the hour;
     - fall back to a forecast when the observation is silent (a forecast is a different claim, and the
       welcome screen is not the place to make it);
     - show a stale report as though it were current — staleness travels with the reading and is said.

   The read is GET /api/now with `lat`/`lon`, the contract the other two surfaces already send. This module
   was written with `latitude`/`longitude`, and the server answered every one of those calls 400 — "The lat
   parameter is required" — a status react-query does not retry, so the welcome had never once shown a
   reading. The endpoint's parameter names are the endpoint's, and they are now the same ones TodaySurface
   and WorkspaceSurface use. */

import { useQuery } from '@tanstack/react-query';
import { getJson, withQuery } from '../api/client';
import type { Envelope, NowReading } from '../api/types';
import { skyGlyph, type SkyGlyph } from '../shell/icons';
import { useWorkingPlace } from '../modules/Evidence';

export type SkyReading = {
  /** The station's own wording, verbatim. Null when it printed none. */
  condition: string | null;
  /** The glyph that wording maps to, or null. Never a default. */
  glyph: SkyGlyph | null;
  /** The temperature as printed, with the unit the source used where it stated one. */
  temperature: string | null;
  unit: string | null;
  station: string | null;
  sourceId: string | null;
  observedAt: string | null;
  stale: boolean;
  /** The label the read returned, or the one the browser is holding. Both are places a reader named or
      chose; a label is never inferred from the coordinates. */
  place: string | null;
  /** The nearest station's distance, when the read states one. */
  distanceKm: number | null;
};

type Station = NonNullable<NonNullable<NowReading['observed']>['stations']>[number];

const field = (station: Station | undefined, ...names: string[]) =>
  (station?.parameters || []).find(entry => names.includes(String((entry as { field?: string }).field || entry.name)));

function read(payload: NowReading | undefined, held: string | null): SkyReading | null {
  const station = (payload?.observed?.stations || [])[0];
  if (!station) return null;
  /* The station's own weather field first, then the cloud wording it printed. A station that reported
     `nebulosity` as cloud has said something about the sky; one that reported neither has not, and the
     glyph stays null rather than being filled in. */
  const wording = field(station, 'weather') || field(station, 'nebulosity');
  const condition = typeof wording?.value === 'string' && wording.value.trim() ? wording.value.trim() : null;
  const temperature = field(station, 'temp', 'temp_c');
  const value = temperature?.value;
  return {
    condition,
    glyph: skyGlyph(condition),
    temperature: value === null || value === undefined || value === '' ? null : String(value),
    unit: temperature?.unit ? String(temperature.unit) : null,
    station: station.name ? String(station.name) : null,
    sourceId: station.source_id ? String(station.source_id) : null,
    observedAt: station.observed_at_utc ? String(station.observed_at_utc) : null,
    stale: station.stale === true,
    place: payload?.point?.label ? String(payload.point.label) : held,
    distanceKm: typeof station.distance_km === 'number' ? station.distance_km : null,
  };
}

/** The right-now reading for the place this browser is holding, or null when it holds none. */
export function useSky(): { data: SkyReading | null; isPending: boolean; isError: boolean } {
  const place = useWorkingPlace();
  const held = place?.label ? String(place.label) : null;
  const query = useQuery({
    queryKey: ['sky', place?.latitude, place?.longitude],
    enabled: Boolean(place),
    staleTime: 300_000,
    retry: false,
    queryFn: () => getJson<Envelope<NowReading>>(withQuery('/api/now', {
      lat: place?.latitude, lon: place?.longitude,
    })),
  });
  return {
    data: place && query.data ? read(query.data.data, held) : null,
    isPending: Boolean(place) && query.isPending,
    isError: query.isError,
  };
}

/* ---- the greeting -----------------------------------------------------------------------------------
   Keyed to the reader's own clock rather than to the solar hour, because a greeting is a social fact and
   not an astronomical one: someone awake at 02:00 is having a night, whatever the sun is doing. */
export function greeting(at: Date): string {
  const hour = at.getHours();
  if (hour < 5) return 'Good night';
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  if (hour < 21) return 'Good evening';
  return 'Good night';
}

/* The same four bands as a catalogue key, because a greeting is chrome and belongs in the reader's own
   language. A greeting is also the one string here that is not a translation of an English sentence but
   the equivalent courtesy in that language — "नमस्कार" is what one says in the afternoon, not a rendering
   of the words "good afternoon". */
export function greetingKey(at: Date): string {
  const hour = at.getHours();
  if (hour < 5) return 'welcome.goodNight';
  if (hour < 12) return 'welcome.goodMorning';
  if (hour < 17) return 'welcome.goodAfternoon';
  if (hour < 21) return 'welcome.goodEvening';
  return 'welcome.goodNight';
}
