/* The catalogue's label is precise and, on screen, a stutter. This collapses it without losing the state.
   Nothing here touches what is sent to the engine or printed on a receipt: those keep the full label,
   because that is what the resolver matched. */
import { describe, expect, it } from 'vitest';
import { shortPlace } from './locale';

describe('a place as a reader should see it', () => {
  it('drops a district that repeats its own city', () => {
    expect(shortPlace('Anand, Anand, State of Gujarāt')).toBe('Anand, Gujarāt');
  });

  it('drops a district that merely qualifies its city', () => {
    expect(shortPlace('Pune, Pune Division, State of Mahārāshtra')).toBe('Pune, Mahārāshtra');
  });

  it('sees through diacritics, so a repeat cannot hide behind a macron', () => {
    expect(shortPlace('Surat, Sūrat, State of Gujarāt')).toBe('Surat, Gujarāt');
  });

  it('keeps a district that is genuinely a different place', () => {
    expect(shortPlace('Ban Sarkāri, Hoshiārpur, Punjab')).toBe('Ban Sarkāri, Punjab');
  });

  it('strips the administrative prefix from the state and nothing else', () => {
    expect(shortPlace('Kochi, Ernākulam, State of Kerala')).toBe('Kochi, Kerala');
    expect(shortPlace('New Delhi, National Capital Territory of Delhi')).toBe('New Delhi, Delhi');
  });

  it('leaves a label it cannot improve exactly as it found it', () => {
    expect(shortPlace('Mumbai')).toBe('Mumbai');
    expect(shortPlace('')).toBe('');
    expect(shortPlace(null)).toBe('');
  });

  it('does not print a city twice when the state carries the same name', () => {
    expect(shortPlace('Goa, North Goa, State of Goa')).toBe('Goa');
  });
});
