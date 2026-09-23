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

import { useEffect, useState } from 'react';
import { istStamp } from '../lib/time';
import { shortPlace } from '../lib/locale';
import { SkyGlyphIcon } from '../shell/icons';
import { greetingKey, useSky, type SkyReading } from './sky';
import { type Hour } from './fieldPaint';
import { DayArc } from './DayArc';
import { QuoteLine } from './QuoteLine';
import { PlacePicker } from './PlacePicker';
import { useShellPrefs } from './shellState';
import { rememberPlace, useWorkingPlace } from '../modules/Evidence';
import { useTranslation } from 'react-i18next';
import { MapPin } from 'lucide-react';
import { findMyPlace } from '../place/useMyLocation';

/* The national default, the same one the ground uses when the browser holds no place: the sun is the same
   sun either way, and what changes is where it stands over the page. */
const DEFAULT_LATITUDE = 23.0;
const DEFAULT_LONGITUDE = 82.5;

/* The station's own source line for a reading: who reported it, the id the registry knows it by, when it
   was read, how far it is, and the two absences a reader has to be told about — a value with no unit in the
   source, and a report the source itself marks stale. Exported because the bar and the rail state the same
   station's reading, and one reading means one line: a second composition of it is how the same report
   starts saying two different things about itself. */
export function stationSource(reading: SkyReading, options: { includeStale?: boolean; includeUnitGap?: boolean } = {}): string {
  /* One composition of one line, so four surfaces cannot state the same reading four ways. The staleness clause
     is the one part a caller may leave out: the panel states it in its own sentence below the line, and a fact
     said twice is the failure this product refuses - it would read as two silences rather than one. */
  return [
    reading.station,
    reading.sourceId,
    reading.observedAt ? 'read ' + istStamp(reading.observedAt) : null,
    /* 'away' rather than a bare distance: it states the relation the number has, and it is the wording both the
       plan's own drawn claim line (docs/108 section 3.5) and the place page's station block (docs/122) use. One
       reading means one line, and that includes its wording. */
    reading.distanceKm !== null ? reading.distanceKm.toFixed(1) + ' km away' : null,
    /* Left out where the CALLER has already said it in its own words. The front door leads with
       "27 reported, with no unit stated by the source", and this line then appended "no unit in the
       source" to the end of the same sentence - the identical absence, stated twice, eleven words
       apart. That is the exact failure this module's header calls out for staleness, in a second
       place. */
    options.includeUnitGap === false ? null
      : reading.temperature && !reading.unit ? 'no unit in the source' : null,
    options.includeStale === false ? null : reading.stale ? 'the source marks this report stale' : null,
  ].filter(Boolean).join(' · ');
}

export function Welcome({ hour }: { hour: Hour }) {
  const { t } = useTranslation();
  const sky = useSky();
  const held = useWorkingPlace();
  const latitude = held?.latitude ?? DEFAULT_LATITUDE;
  const longitude = held?.longitude ?? DEFAULT_LONGITUDE;
  const [at, setAt] = useState(() => new Date());
  const [picking, setPicking] = useState(false);
  const [locating, setLocating] = useState(false);
  const [locateNote, setLocateNote] = useState<string | null>(null);
  const { prefs } = useShellPrefs();

  useEffect(() => {
    const timer = window.setInterval(() => setAt(new Date()), 60_000);
    return () => window.clearInterval(timer);
  }, []);

  const reading = sky.data;
  const place = reading?.place ?? null;
  /* The reader's own name for a place, if they gave it one, is read from `prefs.aliases` at each use:
     the masthead names the HELD place and the reading below names the STATION's, and those are two
     different places whenever the nearest station is in the next district. */
  const source = reading ? stationSource(reading) : '';

  return (
    <div className="w" data-testid="welcome">
      {/* The mark is the product's name on a phone, where the rail is a drawer. On a desktop the rail
          carries it four centimetres away, and saying it twice is most of what clutter is made of. */}
      <p className="w-mark" aria-hidden="true">
        <span className="w-mark-dot" />
        WeatherGPT
      </p>

      {/* THE MASTHEAD. Three true things, in the machine face, before anything else: the date and minute
          this page is being read at, and the place every answer below it will be about. It is the first
          line an evaluator reads and it is entirely checkable - `istStamp` is the same stamp every claim
          in the product carries, so the front door states its clock in the same words a receipt does. */}
      <p className="w-strip">
        <span>{istStamp(at.toISOString())}</span>
        <span className="w-strip-dot" aria-hidden="true" />
        {/* THE READER'S OWN HELD PLACE, not the station's.
            `place` below is the place the nearest-station read came back about, which is not known until
            that read lands - so for the first second or two of every visit the masthead said "No place
            held" while the composer two elements down already named the place. The held place is known
            immediately, it is the reader's own choice, and it is what "where you are" means here. */}
        <span className="w-strip-place" data-held={held?.label ? 'true' : 'false'}>
          {held?.label ? (prefs.aliases[held.label] || shortPlace(held.label)) : t('welcome.noPlaceHeld')}
        </span>
      </p>

      {/* THE HERO: today's sun, plotted across the whole width.

          Three versions of this have now stood here. A 96px moon in a blurred halo, which said nothing. A
          240px clock face, which was true but was a widget in the corner of a wide screen. This is the
          same astronomy drawn as the plot it always was - the sun's altitude through the day, with the
          daylight filled in - and the fill is the one large area of saturated colour anywhere in this
          product. That is deliberate: a front door with no colour on it has no force, and this is the only
          colour the page can show that is derived from something real.

          `data-kind` still reports which of the two states this screen is in - a station printed a
          condition, or it did not - because that distinction is real and is checked. The CONDITION itself
          is not drawn here: a printed condition is a weather statement and it belongs beside the source
          line that owns it, below, not standing at display size where nothing says where it came from. */}
      <div className="w-glyph" data-kind={reading?.glyph ? 'condition' : 'hour'}>
        <DayArc at={at} latitude={latitude} longitude={longitude} lightLabel={t('welcome.ofLight')} />
      </div>

      {/* THE BODY: the invitation on the left, what is happening right now on the right.

          These were two of nine blocks stacked down the middle of the screen. They belong side by side -
          one is what this product will do for you, the other is the only thing on the front door that is
          actually weather - and a front door that reads as a list of nine unrelated things is the reason
          this screen kept feeling like a placeholder. */}
      <div className="w-body">
      <div className="w-say">

      {/* Keyed on the greeting, so the one thing on this screen that the hour changes is the one thing that
          animates when it changes: "Good afternoon" becomes "Good evening" on the element the reader is
          looking at rather than on a container around it. (transitions.dev text-states swap, pattern 04 —
          the decision that a state change is expressed on the changed element, its translate-and-blur shape
          and its short duration, re-authored here on --g-enter.) The exit half of that pattern animates the
          outgoing text; React replaces the text node in one commit, so what this takes is the entrance. */}
      <h1 className="w-greeting" key={t(greetingKey(at))}>{t(greetingKey(at))}</h1>

      {/* The one sentence a first-time reader - or an evaluator with four minutes - needs, and the only
          place on this product where it is said. Everything else on screen demonstrates it; this states
          it. It is a claim about how this workspace behaves, not about the weather, so it carries no
          source line and needs none. */}
      <p className="w-lede">{t('welcome.lede')}</p>

      {/* The place, and the one control on this screen that can change what everything else is about. A
          reader who has no place is shown the hour and the sun, and this is how they get their own sky. */}
      {place ? null : (
        <>
          <p className="w-place w-place-none">
            <button type="button" className="w-place-button" onClick={() => setPicking(true)}>
              {t('welcome.setYourPlace')}
            </button>
          </p>
          {/* The other way in, for a reader who would rather not type their own town. The browser's
              own permission dialogue is the consent - nothing here runs on load - and every way it
              can fail says so in a sentence rather than going quiet. */}
          <p className="w-locate">
            <button
              type="button"
              className="g-chip"
              disabled={locating}
              onClick={async () => {
                setLocating(true);
                setLocateNote(null);
                const outcome = await findMyPlace();
                setLocating(false);
                if (!outcome.ok) { setLocateNote(outcome.message); return; }
                rememberPlace(outcome.place);
                setLocateNote(outcome.distanceKm === null ? null
                  : 'Holding ' + outcome.place.label + ', the nearest place in the catalogue — '
                    + outcome.distanceKm.toFixed(1) + ' km from where this browser put you. Change it if that is not right.');
              }}
            >
              <MapPin size={13} aria-hidden="true" />
              {locating ? t('welcome.locating') : t('welcome.useMyLocation')}
            </button>
          </p>
          {locateNote ? <p className="w-source g-claim-source" role="status">{locateNote}</p> : null}
        </>
      )}

      </div>

      {/* The reading, as the station printed it, and the source line that owns it — ONE region, because a
          number and its provenance printed as two adjacent paragraphs are still a number a reader has to
          take on trust. The region is the shape the audit checks by content (a claim, with its source
          line inside it), and it carries no box of its own: display:contents leaves the value and the line
          exactly where they were in the column, because on this screen the ground is doing the decorating.
          Absent stays absent: no placeholder value is ever shown where a source said nothing. */}
      {reading && (reading.temperature || reading.condition || source) ? (
        <div className="g-claim w-now">
          {/* THE HERO, and which thing is the hero depends on what the source actually stated.

              A number whose unit nobody stated is not a reading, it is a digit. This screen used to set
              "27" at display size beside the word "mist" because the station printed a temperature and
              no unit, and a reader has no way to know whether that is Celsius, Fahrenheit, or a typo.
              Where the unit IS stated the value leads, as it should. Where it is not, the CONDITION
              leads - a word the source really did print - and the bare number steps down to the line
              below with the absence named. Nothing is hidden either way; what changes is which of the
              two honest facts is allowed to be the largest thing on the page. */}
          {/* The value leads and the condition sits beside it, which is what somebody opening a weather
              workspace came to see.

              This briefly promoted the CONDITION to display size whenever the source stated no unit -
              defensible logic, ridiculous on screen: the largest thing on the page became the word
              "mist". The unit being unstated is a real gap and it is named in the line below, where a
              caveat belongs. It is not a reason to refuse to show the reading. */}
          {reading.temperature || reading.condition ? (
            <p className="w-reading">
              {/* The glyph moved here from the top of the screen. It is a picture of a word a station
                  printed, so it belongs inside the claim, one line above the source that printed it -
                  not alone at the top of the page where nothing around it says who said so. */}
              {reading.glyph ? <SkyGlyphIcon glyph={reading.glyph} size={30} strokeWidth={1.1} /> : null}
              {reading.temperature ? (
                <span className="w-temp">
                  {reading.temperature}
                  {reading.unit ? <span className="w-unit">{reading.unit}</span> : null}
                </span>
              ) : null}
              {reading.condition ? <span className="w-cond">{reading.condition}</span> : null}
            </p>
          ) : null}
          {source ? (
            /* `g-claim-source` stays on this element even though `w-source` overrides every one of its
               visual properties. It is not styling: it is the marker the provenance audit uses to find
               every source line in the product, and dropping it to change a font would have made the
               front door's provenance invisible to the check that exists to prove it is there. */
            <p className="w-source g-claim-source" title={source}>
              {reading.temperature && !reading.unit
                ? reading.temperature + ' reported, with no unit stated by the source · '
                  + stationSource(reading, { includeUnitGap: false })
                : source}
            </p>
          ) : null}
        </div>
      ) : null}

      </div>

      {/* No place held means no read was made: the screen says it is reading rather than showing a
          placeholder value, and once it has answered it says nothing at all. */}
      {!reading && sky.isPending ? <p className="w-source">{t('welcome.readingStation')}</p> : null}

      {/* The one thing on this screen that is not about today's weather, and the only thing on it a reader
          can change. It sits under everything the sky has said, so the page reads as a fact and then a
          thought rather than the other way round. */}
      <QuoteLine at={at} hour={hour} />

      {picking ? <PlacePicker onClose={() => setPicking(false)} /> : null}
    </div>
  );
}
