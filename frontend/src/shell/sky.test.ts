import { applySky, phaseFor } from './sky';

const at = (hour: number, minute = 0) => new Date(2026, 8, 17, hour, minute, 0);

describe('the sky phase', () => {
  it('follows the local clock through the six phases', () => {
    expect(phaseFor(at(3))).toBe('night');
    expect(phaseFor(at(6))).toBe('predawn');
    expect(phaseFor(at(7))).toBe('dawn');
    expect(phaseFor(at(12))).toBe('day');
    expect(phaseFor(at(17))).toBe('dusk');
    expect(phaseFor(at(19))).toBe('night');
    expect(phaseFor(at(23, 30))).toBe('night');
  });

  it('follows a sourced sunrise and sunset when one is supplied', () => {
    const sun = { sunrise: new Date(2026, 8, 17, 5, 45).toISOString(), sunset: new Date(2026, 8, 17, 18, 30).toISOString() };
    expect(phaseFor(at(4), sun)).toBe('predawn');
    expect(phaseFor(at(6, 30), sun)).toBe('dawn');
    expect(phaseFor(at(12), sun)).toBe('day');
    expect(phaseFor(at(19), sun)).toBe('dusk');
    expect(phaseFor(at(21), sun)).toBe('night');
  });

  it('ignores an unreadable sun time rather than inventing a phase', () => {
    expect(phaseFor(at(12), { sunrise: 'not a time', sunset: '' })).toBe('day');
  });

  it('writes the phase to the document and returns it', () => {
    const root = document.createElement('div');
    expect(applySky('dusk', root)).toBe('dusk');
    expect(root.getAttribute('data-sky')).toBe('dusk');
  });
});
