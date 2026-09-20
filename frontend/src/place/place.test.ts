/* A place's own address, and the rule that refuses a half-written one.
   ============================================================================
   The rule is the address's rule (docs/115 §3, docs/122): a place is a name and a coordinate pair that parse
   as numbers and fall inside the world, or it is nothing. Every case below is a shape a link can arrive in,
   and each one must be refused rather than half-applied — a page that resolved one coordinate and guessed the
   other would be showing a place no source named. */

import { describe, expect, it } from 'vitest';
import { conversationHref, placeHref, readPlaceAddress, storedConversationHref } from './place';

const read = (query: string) => readPlaceAddress(new URLSearchParams(query));
const KOCHI = { label: 'Kochi, Kerala', latitude: 9.93, longitude: 76.26 };

describe("a place's own address", () => {
  it('accepts a name and a coordinate pair inside the world', () => {
    const found = read('place=Kochi%2C+Kerala&plat=9.93&plon=76.26');
    expect(found.refused).toBeNull();
    expect(found.place).toEqual(KOCHI);
  });

  it('accepts a point on the equator and on the prime meridian, rather than reading 0 as absent', () => {
    const found = read('place=Null+Island&plat=0&plon=0');
    expect(found.place).toEqual({ label: 'Null Island', latitude: 0, longitude: 0 });
  });

  it('refuses an address that names no place', () => {
    const found = read('plat=9.93&plon=76.26');
    expect(found.place).toBeNull();
    expect(found.refused).toMatch(/names no place/);
    expect(found.refused).toMatch(/place=/);
  });

  it('refuses a blank name rather than trimming it into an unnamed point', () => {
    const found = read('place=%20%20&plat=9.93&plon=76.26');
    expect(found.place).toBeNull();
    expect(found.refused).toMatch(/names no place/);
  });

  it('refuses a half-written coordinate pair, and says which half is missing', () => {
    const latitudeOnly = read('place=Kochi%2C+Kerala&plat=9.93');
    expect(latitudeOnly.place).toBeNull();
    expect(latitudeOnly.refused).toMatch(/half-written/);
    expect(latitudeOnly.refused).toMatch(/longitude/);
    expect(latitudeOnly.refused).not.toMatch(/latitude \(plat/);

    const longitudeOnly = read('place=Kochi%2C+Kerala&plon=76.26');
    expect(longitudeOnly.place).toBeNull();
    expect(longitudeOnly.refused).toMatch(/latitude/);
    expect(longitudeOnly.refused).not.toMatch(/longitude \(plon/);

    const empty = read('place=Kochi%2C+Kerala&plat=&plon=');
    expect(empty.place).toBeNull();
    expect(empty.refused).toMatch(/half-written/);
  });

  it('refuses coordinates that are not numbers, naming the one that is wrong', () => {
    const broken = read('place=Kochi%2C+Kerala&plat=9.93N&plon=76.26');
    expect(broken.place).toBeNull();
    expect(broken.refused).toMatch(/not a number/);
    expect(broken.refused).toMatch(/9\.93N/);

    const infinite = read('place=Kochi%2C+Kerala&plat=Infinity&plon=76.26');
    expect(infinite.place).toBeNull();
    expect(infinite.refused).toMatch(/not a number/);
  });

  it('refuses a point outside the world, either coordinate', () => {
    const north = read('place=Nowhere&plat=90.01&plon=76.26');
    expect(north.place).toBeNull();
    expect(north.refused).toMatch(/outside the world/);

    expect(read('place=Nowhere&plat=-90.01&plon=76.26').place).toBeNull();
    expect(read('place=Nowhere&plat=9.93&plon=180.01').place).toBeNull();
    expect(read('place=Nowhere&plat=9.93&plon=-180.01').place).toBeNull();
  });

  it("reads back the address its own place page writes", () => {
    const href = placeHref(KOCHI);
    expect(href.startsWith('#/place?')).toBe(true);
    /* One word from the link docs/115 recorded: the same three names, read by the same rule. */
    expect(read(href.split('?')[1]).place).toEqual(KOCHI);
    expect(new URLSearchParams(href.split('?')[1]).get('plat')).toBe('9.93');
  });

  it('keeps the conversation link shape docs/115 recorded, unchanged', () => {
    const href = conversationHref(KOCHI);
    expect(href.startsWith('#/assistant?')).toBe(true);
    const params = new URLSearchParams(href.split('?')[1]);
    expect(params.get('place')).toBe('Kochi, Kerala');
    expect(params.get('plat')).toBe('9.93');
    expect(params.get('plon')).toBe('76.26');
    expect(storedConversationHref('c1')).toBe('#/assistant?conversation=c1');
  });
});
