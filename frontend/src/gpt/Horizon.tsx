/* The horizon: where the weather stops and the asking starts.
   ============================================================================
   This began as a full-bleed band of filled buildings across the bottom of the window. It was wrong in
   three ways at once and all three came from the same mistake - it was placed BEHIND the interface
   rather than composed WITH it. The chips sat on top of the roofs, "Today across India" landed in the
   middle of a tower, and the whole thing was cut off by the window's edge. Ornament that content has to
   be read through is not ornament, it is noise.

   So it is not in the background layer any more. It is the last element of the welcome column, at the
   column's own width, and nothing overlaps it because nothing is drawn after it. It ends the front door
   the way a rule ends a page - except that this rule means something: everything above it is what the
   sky is doing, and the composer above it is where you ask about that. It appears on the front door and
   nowhere else, because during a conversation the answer is the subject and a skyline is furniture.

   AND IT IS DRAWN, NOT FILLED. Solid silhouettes at four per cent are a grey smear; the same buildings
   as 1.25px strokes at eighteen per cent are an etching - the line stays crisp, the shape stays legible
   at a glance, and it reads as something someone drew rather than as a texture. A weather instrument
   should look like it was engraved, not airbrushed.

   It is an INDIAN roofline, hand-drawn, and that is the point of not reaching for a stock silhouette: a
   shikhara with its finial, a dome between two minarets, rooftop water tanks on legs, mid-rises with
   setbacks. Every weather template ships with the same Manhattan outline. Somebody from the Ministry of
   Earth Sciences should recognise the country before they read a word.

   THE BIRDS cross above it, slowly, on four separate clocks. They are the one moving thing on the page
   that is not the sun. Under `prefers-reduced-motion` they are not drawn at all; the city stays, because
   a silhouette is information about where you are and removing it would take away the thing rather than
   the animation.

   Everything here is aria-hidden and pointer-events: none. It states nothing, so it must never be read
   out and must never be in the way.
*/

/** One bird: the two-arc gull every child draws, which is the only shape that reads as a bird at 9px. */
function Bird({ className }: { className: string }) {
  return (
    <svg className={className} viewBox="0 0 24 10" width="16" height="7" aria-hidden="true" focusable="false">
      <path d="M1 6 Q6 0 11 5 Q16 0 23 6" fill="none" stroke="currentColor" strokeWidth="1.4"
        strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Horizon() {
  return (
    <div className="g-horizon" aria-hidden="true">
      <Bird className="g-bird g-bird-1" />
      <Bird className="g-bird g-bird-2" />
      <Bird className="g-bird g-bird-3" />
      <Bird className="g-bird g-bird-4" />

      <svg className="g-horizon-city" viewBox="0 0 960 96" preserveAspectRatio="xMidYEnd meet" focusable="false">
        {/* One stroke weight for the whole drawing, so it reads as one hand. The ground line runs the full
            width and every building stands on it; nothing floats. */}
        <g fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinejoin="round" strokeLinecap="round">
          <path d="M0 92 H960" />

          {/* Low roofs, and a water tank on legs - the most Indian rooftop object there is. */}
          <path d="M18 92 V78 H60 V92" />
          <path d="M60 92 V70 H96 V92" />
          <path d="M70 70 V62 H86 V70 M74 62 V56 H82 V62" />
          <path d="M104 92 V74 H150 V92" />

          {/* A mid-rise with a setback, and windows enough to say it is lived in. */}
          <path d="M162 92 V52 H214 V92 M176 52 V42 H200 V52" />
          <path d="M172 62 h8 M190 62 h8 M172 74 h8 M190 74 h8" />

          {/* A temple shikhara: the tapered tower, its cap, and the finial above it. */}
          <path d="M240 92 L250 44 Q256 30 262 44 L272 92" />
          <path d="M246 44 H266 M256 44 V30 M256 30 l-5 -6 h10 Z" />

          {/* A dome between two minarets - drawn, not blocked in. */}
          <path d="M322 92 V38 M322 38 a5 5 0 0 1 10 0 V92" />
          <path d="M416 92 V38 M416 38 a5 5 0 0 1 10 0 V92" />
          <path d="M340 92 V64 Q340 34 374 34 Q408 34 408 64 V92" />
          <path d="M374 34 V22 M374 22 l-4 -6 h8 Z" />

          {/* The towers. The tallest thing on the page, with its mast. */}
          <path d="M452 92 V18 H502 V92 M466 18 V8 H488 V18 M477 8 V0" />
          <path d="M462 34 h10 M482 34 h10 M462 50 h10 M482 50 h10 M462 66 h10 M482 66 h10" />
          <path d="M516 92 V46 H556 V92" />
          <path d="M526 58 h8 M540 58 h8 M526 72 h8 M540 72 h8" />

          {/* A stepped block, then housing, then a second shikhara further off and smaller. */}
          <path d="M572 92 V60 H630 V92 M588 60 V48 H616 V60" />
          <path d="M646 92 V72 H698 V92" />
          <path d="M660 72 V64 H682 V72" />
          <path d="M724 92 L731 56 Q736 46 741 56 L748 92" />
          <path d="M729 56 H743 M736 56 V46" />

          {/* And the roofline falls away to low buildings, so the city ends rather than stops. */}
          <path d="M770 92 V68 H816 V92" />
          <path d="M828 92 V78 H876 V92" />
          <path d="M840 78 V70 H858 V78" />
          <path d="M888 92 V74 H942 V92" />
        </g>
      </svg>
    </div>
  );
}
