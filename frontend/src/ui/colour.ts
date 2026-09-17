/* The hazard ramp, named once for the code that draws a published colour. */
export const HAZARD = ['red', 'orange', 'yellow', 'green'] as const;
export type Hazard = (typeof HAZARD)[number];

export function isHazard(value: unknown): value is Hazard {
  return typeof value === 'string' && (HAZARD as readonly string[]).includes(value.trim().toLowerCase());
}
