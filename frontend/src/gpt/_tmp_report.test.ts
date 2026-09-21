import { describe, it } from 'vitest';
import { solarPosition } from './fieldPaint';
import { spectrumAt, type Scheme } from './spectrum';

type RGB = [number, number, number];
function parseHex(hex: string): RGB {
  const h = hex.replace('#', '');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}
function relLum(rgb: RGB): number {
  const c = (b: number) => { const v = b / 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  return 0.2126 * c(rgb[0]) + 0.7152 * c(rgb[1]) + 0.0722 * c(rgb[2]);
}
function contrast(a: RGB, b: RGB): number {
  const x = relLum(a), y = relLum(b);
  const [l, d] = x >= y ? [x, y] : [y, x];
  return (l + 0.05) / (d + 0.05);
}

const PLACES = [
  { name: 'Kanyakumari', latitude: 8.08, longitude: 77.55 },
  { name: 'Nagpur', latitude: 21.15, longitude: 79.09 },
  { name: 'Leh', latitude: 34.16, longitude: 77.58 },
];
const DATES = [Date.UTC(2026, 5, 21, 0, 0, 0), Date.UTC(2026, 11, 21, 0, 0, 0)];

describe('report', () => {
  it('worst paper/bg contrast per scheme', () => {
    for (const scheme of ['system', 'dark', 'light'] as Scheme[]) {
      let worst = Infinity, worstLabel = '';
      for (const place of PLACES) for (const d of DATES) for (let m = 0; m < 1440; m += 15) {
        const at = new Date(d + m * 60_000);
        const pos = solarPosition(place.latitude, place.longitude, at);
        const s = spectrumAt(pos, scheme);
        const r = contrast(parseHex(s['--g-paper']), parseHex(s['--g-bg']));
        if (r < worst) { worst = r; worstLabel = place.name + ' ' + m; }
      }
      console.log(scheme, 'worst paper/bg', worst.toFixed(2), worstLabel);
    }
  });

  it('current spectrum at Nagpur now, both schemes', () => {
    const pos = solarPosition(21.15, 79.09, new Date());
    console.log('altitude', pos.altitude.toFixed(1), 'hourAngle', pos.hourAngle.toFixed(1));
    for (const scheme of ['system', 'dark', 'light'] as Scheme[]) {
      const s = spectrumAt(pos, scheme);
      console.log(scheme, 'bg', s['--g-bg'], 'paper', s['--g-paper'], 'accent', s['--g-accent'], 'sky1', s['--g-sky-1']);
    }
  });
});
