/* The horizon.
   ============================================================================
   Five moving backgrounds were built for this product and every one of them was rejected. Contours that
   were invisible; wind trails that read as woodgrain; a lattice dragged about by the cursor; a firing cell
   array that, on a white room, came out as grey dust scattered over the reading. The note that ended it
   was the right one: they made the surface ugly, and none of them was worth the attention they took.

   So the ground is still now, and what stands on it is drawn rather than computed: a fine-line horizon
   across the foot of the page. It is one continuous silhouette - flat roofs, a dome, a pair of minarets, a
   stepped gopuram, a water tower, a cluster of towers - which is a skyline anywhere in India and nowhere
   in particular. No single monument is quoted, because naming a city this product does not favour would be
   a claim it has no business making.

   IT IS DECORATION AND IT IS STATIC. No animation, no canvas, no frame loop. It is `aria-hidden`, it
   carries no reading, and it is drawn at an opacity where it reads as a horizon rather than as content.
   The one thing on this page that still moves is the light, and the light is the sun. */

/** One silhouette, authored in a 1600x220 box with the ground at y=220. */
const HORIZON =
  // low roofs, left
  'M0 220 L0 186 L38 186 L38 176 L72 176 L72 190 L104 190 L104 168 L128 168 L128 164 L150 164 L150 190 ' +
  'L186 190 L186 150 L196 150 L196 142 L206 150 L206 190 L232 190 L232 172 L268 172 L268 182 L292 182 ' +
  // a dome on a low hall, with its finial
  'L292 160 L300 160 Q300 128 324 128 Q348 128 348 160 L356 160 L356 190 L392 190 L392 176 L410 176 ' +
  // twin minarets
  'L410 96 L418 88 L426 96 L426 176 L444 176 L444 190 L470 190 L470 96 L478 88 L486 96 L486 190 ' +
  'L516 190 L516 164 L556 164 L556 178 L584 178 ' +
  // mid-rise blocks
  'L584 130 L616 130 L616 118 L648 118 L648 152 L676 152 L676 190 L706 190 L706 142 L742 142 L742 190 ' +
  // a stepped gopuram
  'L768 190 L776 158 L784 158 L790 132 L798 132 L804 110 L812 104 L820 110 L826 132 L834 132 L840 158 ' +
  'L848 158 L856 190 L884 190 L884 174 L916 174 L916 186 L946 186 ' +
  // water tower
  'L946 168 L958 168 L958 122 L950 122 L950 112 L988 112 L988 122 L980 122 L980 168 L992 168 L992 190 ' +
  'L1022 190 L1022 156 L1054 156 L1054 190 ' +
  // a tower cluster
  'L1082 190 L1082 108 L1114 108 L1114 88 L1122 80 L1130 88 L1130 108 L1150 108 L1150 190 ' +
  'L1178 190 L1178 138 L1206 138 L1206 126 L1238 126 L1238 190 L1266 190 L1266 160 L1300 160 L1300 148 ' +
  'L1322 148 L1322 190 L1350 190 L1350 170 L1382 170 L1382 182 L1408 182 ' +
  // a second, smaller dome, right
  'L1408 166 L1416 166 Q1416 140 1436 140 Q1456 140 1456 166 L1464 166 L1464 190 L1494 190 L1494 174 ' +
  'L1528 174 L1528 184 L1560 184 L1560 178 L1600 178 L1600 220 Z';

export function Skyline() {
  return (
    <svg
      className="g-skyline-art"
      viewBox="0 0 1600 220"
      preserveAspectRatio="xMidYMax meet"
      aria-hidden="true"
      focusable="false"
    >
      {/* Drawn twice: a filled body for mass and a hairline along its edge, which is what stops a
          silhouette at this opacity reading as a smudge. */}
      <path className="g-skyline-fill" d={HORIZON} />
      <path className="g-skyline-edge" d={HORIZON} />
    </svg>
  );
}
