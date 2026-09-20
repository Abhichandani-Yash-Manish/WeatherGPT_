/* A place's own address, and the rule that refuses a half-written one.
   ============================================================================
   The panel holds a place and writes it into the address (`#/assistant?place=…&plat=…&plon=…`), which
   docs/115 recorded as the link somebody can send. What was missing was a destination: a page that IS the
   place rather than a conversation that happens to be about it. That page is `#/place?…`, and it reads the
   same three names, so the link shape a reader already has differs by one word.

   The refusal rule is the address's own rule, written once so the page and its specs cannot disagree about
   it: a place is a name and a coordinate pair that parse as numbers and fall inside the world, or it is
   nothing. Nothing here decides a place from a question's wording — the label and the point come from the
   address and from the products' own payloads, never from what a sentence mentioned. */

export type PlaceAddress = { label: string; latitude: number; longitude: number };

export type PlaceRead = {
  /** The place the address names, or null when it does not name one. */
  place: PlaceAddress | null;
  /** Why the address was refused, in the product's own words. Null when a place came back. */
  refused: string | null;
};

const WORLD = { latitude: 90, longitude: 180 };

/** The one place a page refuses or accepts an address: name, both coordinates, numbers, inside the world. */
export function readPlaceAddress(params: URLSearchParams): PlaceRead {
  const label = (params.get('place') || '').trim();
  const rawLatitude = (params.get('plat') || '').trim();
  const rawLongitude = (params.get('plon') || '').trim();

  if (!label) {
    return {
      place: null,
      refused: 'This address names no place. A place page needs a name (place=…) as well as coordinates, and '
        + 'a name is never filled in from a pair of numbers.',
    };
  }
  if (!rawLatitude || !rawLongitude) {
    const missing = [!rawLatitude ? 'latitude (plat=…)' : null, !rawLongitude ? 'longitude (plon=…)' : null]
      .filter(Boolean)
      .join(' and ');
    return {
      place: null,
      refused: 'This address is half-written: it names “' + label + '” but gives no ' + missing
        + '. A place is either both coordinates or it is nothing, so nothing is applied here.',
    };
  }
  const latitude = Number(rawLatitude);
  const longitude = Number(rawLongitude);
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
    const broken = [Number.isFinite(latitude) ? null : 'latitude “' + rawLatitude + '”',
      Number.isFinite(longitude) ? null : 'longitude “' + rawLongitude + '”'].filter(Boolean).join(' and ');
    return {
      place: null,
      refused: 'This address states ' + broken + ', which is not a number. A place whose coordinates are not '
        + 'numbers is refused rather than half-applied.',
    };
  }
  if (Math.abs(latitude) > WORLD.latitude || Math.abs(longitude) > WORLD.longitude) {
    return {
      place: null,
      refused: 'This address puts the place at ' + rawLatitude + ', ' + rawLongitude + ', which is outside the '
        + 'world (latitude ±' + WORLD.latitude + ', longitude ±' + WORLD.longitude + '). Nothing is read for a '
        + 'point that cannot be on the earth.',
    };
  }
  return { place: { label, latitude, longitude }, refused: null };
}

/** Where a place's own page lives. The same three names the panel writes, with `place` as the route. */
export function placeHref(place: PlaceAddress): string {
  return '#/place?' + new URLSearchParams({
    place: place.label,
    plat: String(place.latitude),
    plon: String(place.longitude),
  }).toString();
}

/** Back to the conversation about this place — the link shape docs/115 recorded, unchanged. */
export function conversationHref(place: PlaceAddress): string {
  return '#/assistant?' + new URLSearchParams({
    place: place.label,
    plat: String(place.latitude),
    plon: String(place.longitude),
  }).toString();
}

/** A stored conversation, by the id the engine gave it. */
export function storedConversationHref(id: string): string {
  return '#/assistant?' + new URLSearchParams({ conversation: id }).toString();
}
