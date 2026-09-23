/* Setting the place from the front door.
   ============================================================================
   Until now a reader acquired a place by asking a question about one. The welcome screen shows the reader's
   own sky — the sun's position, the station's reading, the ground's colour — and none of it could be given a
   place from the screen itself. This is that control: a native dialog, a search of the same place catalogue
   the palette and the module surfaces read, and one row to choose.

   A row that states coordinates can be chosen; a row that states none is shown as one rather than resolved
   somewhere else. Nothing here invents a place, and nothing is sent anywhere: the catalogue is this machine's
   own. */

import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { MapPin } from 'lucide-react';
import { getJson, withQuery } from '../api/client';
import { rememberPlace } from '../modules/Evidence';

type Match = {
  label?: string | null; name?: string | null; state?: string | null; district?: string | null;
  latitude?: number | null; longitude?: number | null;
  coordinates?: { latitude?: number | null; longitude?: number | null } | null;
};

const labelOf = (row: Match) => String(row.label || row.name || '').trim();
const pointOf = (row: Match) => ({
  latitude: typeof row.latitude === 'number' ? row.latitude : row.coordinates?.latitude,
  longitude: typeof row.longitude === 'number' ? row.longitude : row.coordinates?.longitude,
});

export function PlacePicker({ onClose }: { onClose: () => void }) {
  const box = useRef<HTMLDialogElement | null>(null);
  const trigger = useRef(document.activeElement instanceof HTMLElement ? document.activeElement : null);
  const [term, setTerm] = useState('');
  const query = term.trim();

  useEffect(() => {
    const node = box.current;
    if (!node) return;
    if (typeof node.showModal === 'function') node.showModal();
    else node.setAttribute('open', '');
    return () => { trigger.current?.focus(); };
  }, []);

  const search = useQuery({
    queryKey: ['places', query],
    queryFn: () => getJson<{ data?: { matches?: Match[] } }>(withQuery('/api/places/search', { q: query })),
    enabled: query.length >= 2,
    retry: false,
  });
  const matches = search.data?.data?.matches || [];

  const choose = (row: Match) => {
    const point = pointOf(row);
    if (typeof point.latitude !== 'number' || typeof point.longitude !== 'number') return;
    rememberPlace({ label: labelOf(row), latitude: point.latitude, longitude: point.longitude });
    onClose();
  };

  return (
    <dialog
      ref={box}
      className="g-picker"
      aria-label="Set the place this conversation is about"
      onClose={onClose}
      onCancel={onClose}
      onKeyDown={event => {
        if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); onClose(); }
      }}
      onClick={event => {
        if (event.target !== box.current) return;
        const rect = event.currentTarget.getBoundingClientRect();
        if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) onClose();
      }}
    >
      <h2 className="g-keys-title">Name a place</h2>
      <p className="g-keys-note">
        Choose a place for your next question. You can still ask about somewhere else by naming it in your message.
      </p>
      <label className="sr-only" htmlFor="w-place">Place</label>
      <input
        id="w-place"
        type="search"
        className="g-search"
        value={term}
        onChange={event => setTerm(event.target.value)}
        placeholder="Type at least two characters"
        autoComplete="off"
        autoFocus
      />
      <div className="g-picker-results" role="listbox" aria-label="Places">
        {search.isFetching ? <p className="g-empty-note">Reading the place catalogue…</p> : null}
        {search.isError ? <p className="g-empty-note">The place catalogue did not answer, so nothing is listed. That is a read failure, not an empty catalogue.</p> : null}
        {!search.isFetching && !search.isError && query.length >= 2 && !matches.length ? (
          <p className="g-empty-note">The catalogue returned no place matching “{query}”.</p>
        ) : null}
        {matches.slice(0, 8).map((row, index) => {
          const point = pointOf(row);
          const usable = typeof point.latitude === 'number' && typeof point.longitude === 'number';
          const name = labelOf(row) || 'Unnamed row';
          return (
            <button
              key={name + index}
              type="button"
              className="g-picker-row"
              role="option"
              aria-selected={false}
              disabled={!usable}
              title={usable ? name + ' · ' + point.latitude + ', ' + point.longitude : 'This row states no coordinates'}
              onClick={() => choose(row)}
            >
              <MapPin size={13} aria-hidden="true" />
              <span className="g-picker-name">{name}</span>
              <span className="g-picker-where">
                {usable ? 'coordinates in this row' : 'no coordinates in this row'}
              </span>
            </button>
          );
        })}
      </div>
      <button type="button" className="g-quiet" onClick={onClose}>Close</button>
    </dialog>
  );
}
