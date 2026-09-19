export const PHASES: string[];
export const PALETTES: Record<string, unknown>;
export function planes(
  palette: unknown,
  phase?: string,
): { far: string; mid: string; near: string; ground: string; groundFar: string };
export function rgb(hex: string): unknown;
export function mix(a: unknown, b: unknown, amount: number): unknown;
