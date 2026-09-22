/* Asking this browser where the reader is, and turning that into a place this workspace can answer about.
   ============================================================================
   Two steps, and the second is the one that matters. The browser gives coordinates; every tool here
   takes a NAMED place - the district a warning is published for, the station a reading came from, the
   bulletin a district carries - so a latitude and longitude on their own are not something this product
   can answer about. They are resolved once against the place catalogue and the NAME is what is held.

   IT IS NEVER AUTOMATIC. `navigator.geolocation` prompts, and this is only ever called from a control
   the reader pressed, so the browser's own permission dialogue is the consent. Nothing here runs on
   load, nothing is stored anywhere but this browser, and the coordinates are sent to this machine's own
   engine and to nowhere else.

   EVERY FAILURE IS A SENTENCE, not a silence. Denied, unavailable, timed out, no browser support, and
   "you are somewhere this catalogue does not cover" are five different things and a reader can act on
   four of them. A control that just stops working teaches nothing.
*/
import { getJson, withQuery } from '../api/client';
import type { Envelope } from '../api/types';

export type NearestPlace = {
  name?: string;
  admin1?: string;
  admin2?: string;
  latitude?: number;
  longitude?: number;
  distance_km?: number;
};

type NearestReply = { point: { latitude: number; longitude: number }; match: NearestPlace | null };

export type LocationOutcome =
  | { ok: true; place: { label: string; latitude: number; longitude: number }; distanceKm: number | null }
  | { ok: false; message: string };

/** A label a reader recognises: the place, then its state where the catalogue records one. */
export function labelFor(match: NearestPlace): string {
  return [match.name, match.admin2, match.admin1].filter(Boolean).join(', ');
}

function coordinates(): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      reject(new Error('This browser does not offer a location to pages.'));
      return;
    }
    navigator.geolocation.getCurrentPosition(resolve, reject, {
      /* A coarse fix is enough to name a town and is far quicker and cheaper than a precise one; this
         is not navigation. */
      enableHighAccuracy: false,
      timeout: 12_000,
      maximumAge: 300_000,
    });
  });
}

function why(error: unknown): string {
  const code = (error as GeolocationPositionError | undefined)?.code;
  if (code === 1) return 'This browser refused to share your location. You can allow it in the address bar, or set a place by name.';
  if (code === 2) return 'This browser could not work out where you are. Set a place by name instead.';
  if (code === 3) return 'Finding your location took too long. Try again, or set a place by name.';
  return error instanceof Error && error.message ? error.message : 'Your location could not be read. Set a place by name instead.';
}

/**
 * Ask the browser for a location and resolve it to a catalogue place.
 *
 * Resolves with an outcome rather than throwing: refusing to share a location is an ordinary thing a
 * reader does, not an exception.
 */
export async function findMyPlace(): Promise<LocationOutcome> {
  let position: GeolocationPosition;
  try {
    position = await coordinates();
  } catch (error) {
    return { ok: false, message: why(error) };
  }
  const { latitude, longitude } = position.coords;
  try {
    const reply = await getJson<Envelope<NearestReply>>(
      withQuery('/api/places/nearest', { lat: latitude, lon: longitude }));
    const match = reply.data?.match;
    if (!match || !Number.isFinite(match.latitude) || !Number.isFinite(match.longitude)) {
      return {
        ok: false,
        message: 'You are somewhere this place catalogue does not cover, so there is no place to hold. Set one by name instead.',
      };
    }
    return {
      ok: true,
      place: { label: labelFor(match), latitude: Number(match.latitude), longitude: Number(match.longitude) },
      distanceKm: typeof match.distance_km === 'number' ? match.distance_km : null,
    };
  } catch {
    return { ok: false, message: 'The place catalogue did not answer, so your location could not be named. Set a place by name instead.' };
  }
}
