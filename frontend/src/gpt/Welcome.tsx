/* The welcome screen.
   ============================================================================
   What this replaces: a national warning brief set at display size — "303 districts carry a yellow
   caution today" — which briefed a reader who had not asked for a briefing, and which belongs on the
   Warnings home where someone has gone looking for exactly that. It is not deleted from the product; it
   is one chip away, and it is the whole subject of another home.

   What stands here instead is the reader's own sky, in four elements and no more: a mark, a greeting, the
   place, and the reading a station actually reported. The ground is doing the decorating, so nothing on
   top of it has to — no card, no border, no panel. The type sits directly on the colour, which is the move
   the reference this screen came from is built on.

   The rule this screen is built around: a condition is DRAWN only when a source PRINTED one. The glyph,
   the word and the temperature all come from the same station report and carry its id and its read time.
   When no place is held, or the nearest station printed no weather field, there is no glyph and no word —
   the mark becomes the hour, which is astronomy rather than a claim, and the glass stays empty rather than
   being filled with a zero.

   Three lines were removed from this screen, and each repeated something already said: the brand mark on a
   desktop where the rail carries it already, the hour word under a greeting that states the hour, and
   "name a place and it becomes yours" under a composer whose placeholder asks for exactly that. */

import { useEffect, useMemo, useState } from 'react';
import { istStamp } from '../lib/time';
import { SkyGlyphIcon } from '../shell/icons';
import { greetingKey, useSky } from './sky';
import { solarPosition, type Hour } from './fieldPaint';
import { QuoteLine } from './QuoteLine';
import { PlacePicker } from './PlacePicker';
import { useShellPrefs } from './shellState';
import { useWorkingPlace } from '../modules/Evidence';
import { useTranslation } from 'react-i18next';

/* The national default, the same one the ground uses when the browser holds no place: the sun is the same
   sun either way, and what changes is where it stands over the page. */
const DEFAULT_LATITUDE = 23.0;
const DEFAULT_LONGITUDE = 82.5;

export function Welcome({ hour }: { hour: Hour }) {
  const { t } = useTranslation();
  const sky = useSky();
  const held = useWorkingPlace();
  const latitude = held?.latitude ?? DEFAULT_LATITUDE;
  const longitude = held?.longitude ?? DEFAULT_LONGITUDE;
  const [at, setAt] = useState(() => new Date());
  const [picking, setPicking] = useState(false);
  const { prefs } = useShellPrefs();

  useEffect(() => {
    const timer = window.setInterval(() => setAt(new Date()), 60_000);
    return () => window.clearInterval(timer);
  }, []);

  const reading = sky.data;
  const place = reading?.place ?? null;
  /* The reader's own name for this place, if they gave it one. A display name only: what is sent to the
     engine is the label the catalogue returned, and the title above says so. */
  const alias = place ? prefs.aliases[place] : '';
  /* The station's own number, and its own unit only where the source stated one. A value with no unit is
     printed without a unit and said so below, rather than being given a scale the source never wrote. */
  const source = reading
    ? [
        reading.station,
        reading.sourceId,
        reading.observedAt ? 'read ' + istStamp(reading.observedAt) : null,
        reading.distanceKm !== null ? reading.distanceKm.toFixed(1) + ' km' : null,
        reading.temperature && !reading.unit ? 'no unit in the source' : null,
        reading.stale ? 'the source marks this report stale' : null,
      ].filter(Boolean).join(' · ')
    : '';

  return (
    <div className="w" data-testid="welcome">
      {/* The mark is the product's name on a phone, where the rail is a drawer. On a desktop the rail
          carries it four centimetres away, and saying it twice is most of what clutter is made of. */}
      <p className="w-mark" aria-hidden="true">
        <span className="w-mark-dot" />
        WeatherGPT
      </p>

      {/* The glyph is the condition when a station printed one, and the hour otherwise. Both are honest;
          only one of them is a weather statement, and it is the one that carries a source. */}
      <div className="w-glyph" data-kind={reading?.glyph ? 'condition' : 'hour'} aria-hidden="true">
        {reading?.glyph ? (
          <>
            <span className="w-bloom" />
            <SkyGlyphIcon glyph={reading.glyph} size={74} strokeWidth={0.95} />
          </>
        ) : (
          <HourDial at={at} latitude={latitude} longitude={longitude} />
        )}
      </div>

      <h1 className="w-greeting">{t(greetingKey(at))}</h1>

      {/* The place, and the one control on this screen that can change what everything else is about. A
          reader who has no place is shown the hour and the sun, and this is how they get their own sky. */}
      {place ? (
        <p className="w-place">
          <button type="button" className="w-place-button" onClick={() => setPicking(true)} title={'Change the place — ' + place}>
            {alias || place}
          </button>
        </p>
      ) : (
        <p className="w-place w-place-none">
          <button type="button" className="w-place-button" onClick={() => setPicking(true)}>
            {t('welcome.setYourPlace')}
          </button>
        </p>
      )}

      {/* The reading, as the station printed it. Absent stays absent: no placeholder value is ever shown
          where a source said nothing. */}
      {reading && (reading.temperature || reading.condition) ? (
        <p className="w-reading">
          {reading.temperature ? (
            <span className="w-temp">
              {reading.temperature}
              {reading.unit ? <span className="w-unit">{reading.unit}</span> : null}
            </span>
          ) : null}
          {reading.condition ? <span className="w-cond">{reading.condition}</span> : null}
        </p>
      ) : null}

      {source || sky.isPending ? (
        <p className="w-source">{sky.isPending ? t('welcome.readingStation') : source}</p>
      ) : null}

      {/* The one thing on this screen that is not about today's weather, and the only thing on it a reader
          can change. It sits under everything the sky has said, so the page reads as a fact and then a
          thought rather than the other way round. */}
      <QuoteLine at={at} hour={hour} />

      {picking ? <PlacePicker onClose={() => setPicking(false)} /> : null}
    </div>
  );
}

/* The hour, drawn as the instrument it is: the sun's own position over a horizon at this place and minute —
   altitude for the height, hour angle for the east–west place, so the disc sits on the line at dawn and dusk
   and stands high at solar noon. This is astronomy. It says what time of day it is, and nothing at all about
   the weather, which is why it is drawn quietly and why a station report takes the mark from it.

   There was a semicircular arc here for the sun's path, and it was removed for a reason worth keeping: a
   half-circle says the sun rises due east, sets due west and passes through the zenith, and at 23°N in
   December none of that is true. A mark drawn from astronomy does not get to be approximate astronomy, so
   what is left are the two things that are exactly right — where the sun is, and how high above the line.

   A crescent when the sun is below civil twilight, which is the same edge the ground changes colour at. */
function HourDial({ at, latitude, longitude }: { at: Date; latitude: number; longitude: number }) {
  const { altitude, hourAngle } = useMemo(
    () => solarPosition(latitude, longitude, at),
    [latitude, longitude, at],
  );
  const night = altitude < -6;
  /* −90°..+90° across the dial and 0°..90° up it, both clamped so a disc never leaves its box. */
  const x = 32 + (Math.min(90, Math.max(-90, hourAngle)) / 90) * 21;
  const y = 46 - (Math.min(90, Math.max(0, altitude)) / 90) * 28;
  /* The glow is a style layer rather than an SVG gradient, because it lights in the ground's own accent
     token and a gradient stop cannot read a custom property. It is painted 180% of the mark's width,
     centred on it, so a point at x/64 of the mark sits at ((x/64) + 0.4) / 1.8 of the glow. */
  const glow = (v: number) => (((v / 64 + 0.4) / 1.8) * 100).toFixed(1) + '%';

  return (
    <>
      <span className="w-bloom" style={night ? undefined : ({ '--w-x': glow(x), '--w-y': glow(y) } as React.CSSProperties)} />
      {/* Ids are literal, not generated: a fragment reference into a generated React id does not resolve,
          which is how the first version of this mark silently lost its horizon line. */}
      <svg viewBox="0 0 64 64" width={96} height={96} aria-hidden="true">
        {/* A horizon, not a rule: it fades out at both ends. userSpaceOnUse, not the default: a
            horizontal line has a bounding box with no height in it, and a gradient measured on that box is
            never painted at all — which is how this line went missing without a single error being raised. */}
        <linearGradient id="w-horizon-fade" gradientUnits="userSpaceOnUse" x1="3" y1="0" x2="61" y2="0">
          <stop offset="0" stopColor="currentColor" stopOpacity="0.08" />
          <stop offset="0.22" stopColor="currentColor" stopOpacity="0.5" />
          <stop offset="0.78" stopColor="currentColor" stopOpacity="0.5" />
          <stop offset="1" stopColor="currentColor" stopOpacity="0.08" />
        </linearGradient>
        <line x1="3" y1="46" x2="61" y2="46" stroke="url(#w-horizon-fade)" strokeWidth="1.4" />
        {night ? (
          <>
            <mask id="w-moon-cut">
              <rect width="64" height="64" fill="#fff" />
              <circle cx="37" cy="21.6" r="8.2" fill="#000" />
            </mask>
            <circle cx="32" cy="26" r="8.4" style={{ fill: 'var(--g-accent)' }} mask="url(#w-moon-cut)" />
          </>
        ) : (
          /* The disc is the one lit thing on this screen that is not a reading: it is the sun, and it is
             where the sun is. Nothing else in the mark carries the accent. */
          <circle cx={x} cy={y} r="7" style={{ fill: 'var(--g-accent)' }} />
        )}
      </svg>
    </>
  );
}
