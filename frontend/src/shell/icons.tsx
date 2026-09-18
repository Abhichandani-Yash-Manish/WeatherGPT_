/* Line icons for the chrome, drawn inline so the page loads nothing off-origin. The paths follow the lucide set
   (ISC licence) that the dashboard reference used. Every icon is decorative (aria-hidden): the control carrying it
   always has its own name. The sky glyphs are chosen only from words a station printed; see skyGlyph. */
import type { SVGProps } from 'react';

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function Icon({ size = 16, children, ...rest }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false" {...rest}>
      {children}
    </svg>
  );
}

export const SearchIcon = (p: IconProps) => <Icon {...p}><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></Icon>;
export const BellIcon = (p: IconProps) => <Icon {...p}><path d="M10.268 21a2 2 0 0 0 3.464 0" /><path d="M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326" /></Icon>;
export const SettingsIcon = (p: IconProps) => <Icon {...p}><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" /><circle cx="12" cy="12" r="3" /></Icon>;
export const LockIcon = (p: IconProps) => <Icon {...p}><rect width="18" height="11" x="3" y="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></Icon>;
export const CommandIcon = (p: IconProps) => <Icon {...p}><path d="M15 6v12a3 3 0 1 0 3-3H6a3 3 0 1 0 3 3V6a3 3 0 1 0-3 3h12a3 3 0 1 0-3-3" /></Icon>;
export const ChevronDownIcon = (p: IconProps) => <Icon {...p}><path d="m6 9 6 6 6-6" /></Icon>;
export const MenuIcon = (p: IconProps) => <Icon {...p}><path d="M4 6h16M4 12h16M4 18h16" /></Icon>;
export const DropletIcon = (p: IconProps) => <Icon {...p}><path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z" /></Icon>;
export const WindIcon = (p: IconProps) => <Icon {...p}><path d="M12.8 19.6A2 2 0 1 0 14 16H2" /><path d="M17.5 8a2.5 2.5 0 1 1 2 4H2" /><path d="M9.8 4.4A2 2 0 1 1 11 8H2" /></Icon>;
export const ThermometerIcon = (p: IconProps) => <Icon {...p}><path d="M14 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z" /></Icon>;
export const EyeIcon = (p: IconProps) => <Icon {...p}><path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0" /><circle cx="12" cy="12" r="3" /></Icon>;
export const GaugeIcon = (p: IconProps) => <Icon {...p}><path d="m12 14 4-4" /><path d="M3.34 19a10 10 0 1 1 17.32 0" /></Icon>;
export const SparkleIcon = (p: IconProps) => <Icon {...p}><path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z" /></Icon>;
export const SendIcon = (p: IconProps) => <Icon {...p}><path d="M12 19V5" /><path d="m5 12 7-7 7 7" /></Icon>;
export const CloudIcon = (p: IconProps) => <Icon {...p}><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z" /></Icon>;
export const CloudRainIcon = (p: IconProps) => <Icon {...p}><path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242" /><path d="M16 14v6M8 14v6M12 16v6" /></Icon>;
export const CloudLightningIcon = (p: IconProps) => <Icon {...p}><path d="M6 16.326A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 .5 8.973" /><path d="m13 12-3 5h4l-3 5" /></Icon>;
export const HazeIcon = (p: IconProps) => <Icon {...p}><path d="M3 8h13M3 12h18M3 16h13M7 20h10" /></Icon>;
export const ClearSkyIcon = (p: IconProps) => <Icon {...p}><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" /></Icon>;

export type SkyGlyph = 'storm' | 'rain' | 'haze' | 'cloud' | 'clear';

/** A presentation glyph for text a station printed, or null when the text names nothing it can show. The word
    list is literal: a glyph is drawn only when the printed text itself says storm, rain, haze, cloud or clear. */
export function skyGlyph(printed: string | null | undefined): SkyGlyph | null {
  const text = (printed || '').toLowerCase();
  if (!text.trim()) return null;
  if (/thunder|\bts\b|lightning/.test(text)) return 'storm';
  if (/rain|drizzle|shower/.test(text)) return 'rain';
  if (/haze|mist|fog|smoke|dust/.test(text)) return 'haze';
  if (/cloud|overcast/.test(text)) return 'cloud';
  if (/\bclear\b|cavok|no significant cloud|\bnsc\b|\bskc\b/.test(text)) return 'clear';
  return null;
}

export function SkyGlyphIcon({ glyph, size = 28 }: { glyph: SkyGlyph; size?: number }) {
  const props = { size, strokeWidth: 1.6 };
  if (glyph === 'storm') return <CloudLightningIcon {...props} />;
  if (glyph === 'rain') return <CloudRainIcon {...props} />;
  if (glyph === 'haze') return <HazeIcon {...props} />;
  if (glyph === 'cloud') return <CloudIcon {...props} />;
  return <ClearSkyIcon {...props} />;
}
