/* The horizon: a city the page is standing in, and birds over it.
   ============================================================================
   The ground is astronomy — the sun's real altitude at the reader's own latitude, drifting all day. What it
   had no sense of was PLACE. This is the other half of "where am I": a skyline along the bottom edge, drawn
   in the ground's own ink at four to seven per cent, so it is felt before it is seen.

   It is an INDIAN skyline and that is the whole point of drawing one by hand rather than reaching for a
   stock silhouette. A shikhara with its finial, a dome between two minarets, rooftop water tanks on legs,
   mid-rise blocks with setbacks, and two towers — the roofline of an actual Indian city rather than the
   Manhattan outline every weather template ships with. A judge from the Ministry of Earth Sciences should
   recognise the country before they read a word.

   Two layers, because one flat silhouette reads as a sticker. The far ridge is fainter, shorter and drifts
   a few pixels; the near ridge is darker and still. That difference is the entire depth effect and it costs
   two divs.

   THE BIRDS are four strokes on a long, slow crossing — around a hundred seconds to traverse, with a small
   vertical drift so the path is not a ruled line. They are the one moving thing on the page that is not the
   sun, and they are deliberately hard to catch: the page should feel inhabited when you glance up from an
   answer, not perform for you while you read one.

   Everything here is aria-hidden and pointer-events: none. It states nothing, so it must never be read out
   and must never be in the way. Under `prefers-reduced-motion` the birds are not drawn at all and the ridge
   does not drift — a decorative animation is exactly what that preference is for.
*/

/** One bird: the two-arc gull every child draws, which is the only shape that reads as a bird at 9px. */
function Bird({ className }: { className: string }) {
  return (
    <svg className={className} viewBox="0 0 24 10" width="18" height="8" aria-hidden="true" focusable="false">
      <path d="M1 6 Q6 0 11 5 Q16 0 23 6" fill="none" stroke="currentColor" strokeWidth="1.3"
        strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Horizon() {
  return (
    <div className="g-horizon" aria-hidden="true">
      {/* The far ridge: lower, paler, and the layer that drifts. */}
      <svg className="g-horizon-far" viewBox="0 0 1440 120" preserveAspectRatio="none" focusable="false">
        <path fill="currentColor" d="
          M0 120 V96 h44 v-14 h30 v14 h38 V72 h52 v48 h26 V84 h34 v-10 h28 v10 h30 v46 h24 V66 h46 v54 h30
          V88 h58 v-16 h26 v16 h40 v48 h28 V78 h50 v42 h34 V92 h36 v-12 h30 v12 h44 v40 h30 V70 h44 v50 h28
          V86 h54 v34 h30 V74 h40 v46 h26 V94 h48 v26 h32 V80 h42 v40 h30 V90 h56 v30 h28 V76 h46 v44 h30
          V98 h40 v22 h34 V84 h44 v36 h30 V92 h52 v28 h30 V88 h38 v32 Z" />
      </svg>

      {/* The near ridge, with the buildings that make it this country. */}
      <svg className="g-horizon-near" viewBox="0 0 1440 140" preserveAspectRatio="none" focusable="false">
        <g fill="currentColor">
          {/* Low roofline running the whole width, so nothing floats. */}
          <rect x="0" y="112" width="1440" height="28" />

          {/* Rooftop water tanks on legs — the most Indian rooftop object there is. */}
          <rect x="66" y="96" width="26" height="12" rx="2" />
          <rect x="72" y="108" width="3" height="6" />
          <rect x="84" y="108" width="3" height="6" />
          <rect x="612" y="92" width="22" height="10" rx="2" />
          <rect x="617" y="102" width="3" height="10" />
          <rect x="627" y="102" width="3" height="10" />

          {/* Mid-rise blocks with setbacks. */}
          <rect x="130" y="74" width="62" height="42" />
          <rect x="146" y="62" width="30" height="14" />
          <rect x="232" y="88" width="48" height="28" />
          <rect x="300" y="68" width="40" height="48" />

          {/* A temple shikhara: tapered tower, capped, with its finial. */}
          <path d="M392 116 L400 58 Q406 44 412 58 L420 116 Z" />
          <rect x="398" y="50" width="16" height="6" rx="2" />
          <rect x="404" y="38" width="4" height="12" />
          <circle cx="406" cy="35" r="4" />

          {/* A dome between two minarets. */}
          <rect x="520" y="60" width="9" height="56" />
          <circle cx="524.5" cy="56" r="6" />
          <rect x="604" y="60" width="9" height="56" />
          <circle cx="608.5" cy="56" r="6" />
          <path d="M534 116 V88 Q534 58 568 58 Q602 58 602 88 V116 Z" />
          <rect x="564" y="44" width="4" height="14" />
          <circle cx="566" cy="41" r="4" />

          {/* The towers. */}
          <rect x="700" y="34" width="54" height="82" />
          <rect x="714" y="22" width="26" height="14" />
          <rect x="725" y="6" width="4" height="18" />
          <rect x="778" y="56" width="44" height="60" />
          <rect x="848" y="44" width="50" height="72" />
          <rect x="862" y="32" width="22" height="14" />

          {/* A stepped block, then housing, then a second shikhara further off. */}
          <rect x="930" y="80" width="70" height="36" />
          <rect x="948" y="66" width="36" height="16" />
          <rect x="1034" y="92" width="56" height="24" />
          <rect x="1050" y="82" width="24" height="12" />
          <path d="M1130 116 L1136 74 Q1141 62 1146 74 L1152 116 Z" />
          <rect x="1136" y="60" width="4" height="14" />

          {/* And the far edge back down to low roofs, so the city ends rather than stops. */}
          <rect x="1196" y="88" width="52" height="28" />
          <rect x="1214" y="76" width="18" height="14" />
          <rect x="1290" y="98" width="64" height="18" />
          <rect x="1386" y="92" width="44" height="24" />
        </g>
      </svg>

      <Bird className="g-bird g-bird-1" />
      <Bird className="g-bird g-bird-2" />
      <Bird className="g-bird g-bird-3" />
      <Bird className="g-bird g-bird-4" />
    </div>
  );
}
