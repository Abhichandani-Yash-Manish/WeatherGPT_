/* The scene library is plain .mjs; these are the shapes the app uses, declared where TypeScript can see them. */
export const LANDMARKS: Record<string, { label: string; city: string; build: () => { d: string; rule: string } }>;
export const LANDMARK_BOX: { w: number; h: number };
export function landmarkFor(place: unknown): string;
