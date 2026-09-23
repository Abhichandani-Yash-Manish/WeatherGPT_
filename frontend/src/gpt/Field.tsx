/* The ground.
   ============================================================================
   The layers behind everything, and the one element on this page that is allowed to move on its own.

   THE LIGHT IS REAL. The hour is decided by the sun's actual altitude and hour angle at the reader's own
   held place (fieldPaint.ts), and `meridianSpectrumAt` turns that into the thirty-two custom properties the
   whole stylesheet is written against. The page therefore drifts continuously through the day - first
   light is warm, high sun is the selected reference exactly, dusk is a rose-grey, midnight is the coolest
   and the most quiet - and it never once leaves the light family, because the direction chosen on
   22 September was a calm light page for a reader who may well be reading it at midnight.

   That is the distinction the first implementation of Meridian lost. It froze the selected reference into
   one set of hex values and replaced this component with a single raster image. Frozen is not calm; it is
   just frozen, and a page that is byte-for-byte identical at 06:00 and at 23:00 is a page nothing is
   looking after.

   THE WEATHER IS REAL TOO, WHERE THERE IS ANY. The mood layer - the quietest of the five - takes its
   colour from the condition the nearest station actually PRINTED, at a fifth of full strength, and a
   station that printed none leaves the ground as astronomy alone. Nothing here invents a condition.

   THE GROUND IS STILL. Five moving backgrounds were built here and all five were rejected - contours that
   could not be seen, wind that read as woodgrain, a lattice dragged by the cursor, a cell array that came
   out as grey dust over the reading. What stands there now is a drawn horizon (Skyline.tsx): static,
   aria-hidden, carrying no reading. The only thing on this page that moves is the light, and the light is
   the sun. */

import { useEffect, useRef } from 'react';
import { SkyGlyphIcon, type SkyGlyph } from '../shell/icons';
import { solarPosition } from './fieldPaint';
import { applySpectrum, clearSpectrum, meridianSpectrumAt } from './spectrum';
import { Skyline } from './Skyline';
import { useWorkingPlace } from '../modules/Evidence';

/* The centre of the country, for a reader who has held no place yet. The welcome screen reads the held
   place exactly the same way, so the two screens are never lit from two different suns. */
const DEFAULT_LATITUDE = 23.0;
const DEFAULT_LONGITUDE = 82.5;

export function Field({ expanded, sky = null }: { expanded: boolean; sky?: SkyGlyph | null }) {
  const held = useWorkingPlace();
  const latitude = held?.latitude ?? DEFAULT_LATITUDE;
  const longitude = held?.longitude ?? DEFAULT_LONGITUDE;
  const field = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const root = document.documentElement;
    const previous = root.dataset.design;
    root.dataset.design = 'meridian';
    return () => {
      if (previous) root.dataset.design = previous;
      else delete root.dataset.design;
    };
  }, []);

  /* The palette, repainted every minute from the sun's own position. A minute is finer than a reader can
     tell apart and coarse enough to cost nothing: this is a colour, not an animation, so it needs no rAF
     loop and is not gated by reduced-motion - the CSS transitions that turn a minute-to-minute change into
     a visible drift are the ones the stylesheets already hold under that preference. */
  useEffect(() => {
    const root = document.documentElement;
    const paint = () => {
      const position = solarPosition(latitude, longitude, new Date());
      applySpectrum(root, meridianSpectrumAt(position));

      /* THE LIGHT IN THE ROOM IS THE SUN, AND IT IS WHERE THE SUN IS.
         ------------------------------------------------------------------------------------------------
         This is the one idea in the whole interface that is only available to this product. The glow
         behind the page is not decoration placed by eye: its position is the sun's actual position at the
         reader's own held place, from the same solver the day arc is plotted from. It rises in the east -
         screen left - arcs over through the morning, and sets on the right. Below the horizon it sinks off
         the bottom of the page and the warm light goes out, leaving only the cool ambient behind.

         So the arc at the top of the front door and the light behind the whole page are the same fact
         stated twice, in two registers: one you read, one you only feel. And at four in the afternoon the
         page is lit from the west, because it is.

         Written as custom properties on the ground element, at the same minute cadence as the palette, and
         transitioned over a minute in CSS so the sun glides rather than steps. */
      const ground = field.current;
      if (ground) {
        /* Hour angle runs -90 at sunrise to +90 at sunset, which is already an east-west axis. */
        const x = 50 + Math.max(-1, Math.min(1, position.hourAngle / 90)) * 46;
        /* Altitude puts it high at noon and below the fold at night. */
        const y = 56 - Math.max(-1, Math.min(1, position.altitude / 90)) * 46;
        /* How much of the warm light is on at all. Fades through civil twilight rather than snapping off
           at the horizon, because that is what the sky does. */
        const lit = Math.max(0, Math.min(1, (position.altitude + 6) / 12));
        ground.style.setProperty('--sun-x', x.toFixed(2) + '%');
        ground.style.setProperty('--sun-y', y.toFixed(2) + '%');
        ground.style.setProperty('--sun-lit', lit.toFixed(3));
      }
    };
    paint();
    const timer = window.setInterval(paint, 60_000);
    return () => {
      window.clearInterval(timer);
      clearSpectrum(root);
    };
  }, [latitude, longitude]);

  return (
    <div className="g-field" ref={field} data-expanded={String(expanded)} data-sky={sky || 'none'} aria-hidden="true">
      <div className="g-field-sky" />
      <div className="g-field-halo" />
      <div className="g-field-mood" />
      {/* THE TWO LIGHTS. The sun, where the sun actually is, and the ambient sky behind it.

          It is CSS, not canvas, and that is the whole reason it is smooth: two very large radial
          gradients moved on transform and opacity are composited on the GPU and cost the main thread
          nothing, where the same shapes redrawn per frame on canvas were the most expensive fills in the
          product. They are positioned from --sun-x / --sun-y, which Field writes once a minute, and they
          glide between those positions over a minute rather than stepping. */}
      <div className="g-bloom" data-bloom="sun" />
      <div className="g-bloom" data-bloom="sky" />
      <Skyline />
      <div className="g-field-grain" />
      <div className="g-field-vignette" />
      {sky ? (
        <div className="g-field-mark">
          <SkyGlyphIcon glyph={sky} size={320} strokeWidth={0.32} />
        </div>
      ) : null}
    </div>
  );
}
