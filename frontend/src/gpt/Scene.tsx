/* The layered scene, wired in.
   ============================================================================
   The scene library in src/scene/ was built and then never imported by the app: eleven landmarks, a palette for
   each of the four phases, and plane tints derived from the palette. This is the two layers the Firewatch/Overdrop
   reference is actually about, and the two the objective names:

   1. **the mid silhouette** — a ridge behind everything, tinted for depth by planes().mid;
   2. **the landmark** — the place's own building, tinted by planes().near, standing on the horizon.

   Which landmark is not a guess about a city: landmarkFor() matches the place name, then the region, then falls
   back to a skyline. It is drawing, so it is here, and the legend at the foot says so.

   No colour is invented here either: the fills come from the scene's own palette for the phase, so the ridge and
   the landmark belong to the same hour the sky does. */

import { useMemo } from 'react';
import { LANDMARK_BOX, LANDMARKS, landmarkFor } from '../scene/landmarks.mjs';
import { PALETTES, planes } from '../scene/palettes.mjs';

export type ScenePhase = 'daybreak' | 'noon' | 'golden' | 'night';

export type SceneProps = { place: string | null | undefined; phase: ScenePhase };

/* A builder returns the path and the fill rule that goes with it: the openings in a landmark are cut with
   fill-rule evenodd rather than painted in the sky colour, so a building stays correct against any sky. */
type Shape = { d: string; rule: string };

export function Scene({ place, phase }: SceneProps) {
  const key = landmarkFor(place);
  const entry = LANDMARKS[key] || LANDMARKS.skyline;
  /* The shape is built once per landmark: the builders are pure, they take no arguments and they return a path in
     the landmark's own 480 x 340 box with its baseline at y = 340. */
  const landmark = useMemo(() => entry.build() as Shape, [entry]);
  const ridge = useMemo(() => LANDMARKS.himalaya.build() as Shape, []);
  const tint = planes(PALETTES[phase] || PALETTES.noon, phase);

  return (
    <div className="g-scene" key={key + phase} aria-hidden="true">
      {/* The middle distance: a stretched ridge, so the landmark has something to stand in front of. */}
      <svg className="g-scene-back" viewBox={`0 0 ${LANDMARK_BOX.w} ${LANDMARK_BOX.h}`} preserveAspectRatio="none">
        <path d={ridge.d} fillRule={ridge.rule as 'evenodd'} fill={tint.mid} />
      </svg>
      {/* The focal layer: the place's own building, or a skyline when nothing matches. */}
      <svg className="g-scene-front" viewBox={`0 0 ${LANDMARK_BOX.w} ${LANDMARK_BOX.h}`} preserveAspectRatio="xMidYMax meet">
        {/* One tint for the landmark, its distance carried by opacity instead of by two different planes. Measured
            on the captures: a darker fill alone made it a black cut-out at noon, and a lighter fill made it vanish.
            The near plane with the light hours holding it back reads as a building in the middle distance. */}
        <path d={landmark.d} fillRule={landmark.rule as 'evenodd'} fill={tint.near} />
      </svg>
    </div>
  );
}
