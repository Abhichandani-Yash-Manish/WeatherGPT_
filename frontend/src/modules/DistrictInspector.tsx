/* The district inspector beside the Today map.

   Three states, and each one is built from the rows the read already returned, so opening it asks the
   product nothing new:

   1. A district is selected: its edition, its age at this read, and every published day-row with the colour
      and the hazard wording as printed, the day covering today marked. Two actions leave the surface: the
      district's own page on the warnings surface, and the same question in the conversation.
   2. A state is selected in the filter bar: that state's districts with the colour each published.
   3. Nothing is selected: the states this read returned, ordered by how many of their districts published a
      colour for the day being inspected, with the colour most of them published. Choosing one filters the map.

   A district with no warning row is still selectable on the figure, and this panel says so in words rather
   than leaving the space empty. */
import { ArrowUpRight, MessageSquare, MapPin, ShieldAlert } from 'lucide-react';
import { count, orNot } from '../lib/format';
import { NOT_RECORDED, ColourTag } from './Evidence';
import { Button } from '../ui/kit';
import type { MapWarningRow, MapDay } from './DistrictRiskMap';

const RAMP = ['red', 'orange', 'yellow', 'green'];
const SEVERITY: Record<string, number> = { red: 0, orange: 1, yellow: 2, green: 3, unset: 8 };

function statedColour(day: MapDay | null | undefined): string | null {
  const value = day && typeof day.colour === 'string' ? day.colour.trim().toLowerCase() : '';
  return RAMP.includes(value) ? value : null;
}

function dayWording(day: MapDay): string {
  if (day.source_text) return day.source_text;
  if (day.hazards && day.hazards.length) return day.hazards.join(', ');
  if (day.hazard_codes && day.hazard_codes.length) return 'hazard codes ' + day.hazard_codes.join(', ');
  return day.quiet === true ? 'no hazard published in this product for this day' : 'no hazard wording published';
}

function dayWhen(day: MapDay): string {
  const date = day.date_local || day.date_utc;
  if (date) return String(date).slice(0, 10);
  return day.label ? day.label : day.day !== undefined ? 'day ' + day.day : 'day not stated';
}

export function DistrictInspector({ rows, selectedKey, dayIndex, statePick, onSelect, onState, askHref, warningsHref }: {
  rows: MapWarningRow[];
  selectedKey: string | null;
  dayIndex: number | null;
  statePick: string;
  onSelect: (key: string) => void;
  onState: (state: string) => void;
  askHref: (question: string) => string;
  warningsHref: (district: string) => string;
}): JSX.Element {
  const selected = selectedKey ? rows.find(row => row.key === selectedKey) || null : null;

  if (selected) {
    const days = (selected.days || []).slice().sort((left, right) => Number(left.day || 0) - Number(right.day || 0));
    const today = dayIndex === null ? days.find(day => day.is_today === true) || null : days.find(day => day.day === dayIndex) || null;
    const name = selected.district || 'name not stated in this read';
    return (
      <section className="glass-soft inspector p-3" data-testid="today-inspector-district" aria-live="polite">
        <div className="inspector-head">
          <div className="min-w-0">
            <p className="eyebrow m-0 flex items-center gap-2"><MapPin size={13} aria-hidden="true" />District inspector</p>
            <h3 className="inspector-title mt-1">{name}</h3>
            <p className="module-note m-0">{orNot(selected.state, 'state not stated in this read')}</p>
          </div>
          <Button size="icon-sm" variant="subtle" aria-label="Close the district inspector" onClick={() => onSelect('')}>×</Button>
        </div>

        <dl className="module-facts glass-soft overflow-hidden">
          <div className="fact-row">
            <dt className="module-fact-label">Edition</dt>
            <dd className="fact-value evidence">{orNot(selected.bulletin_date, NOT_RECORDED)}</dd>
          </div>
          <div className="fact-row">
            <dt className="module-fact-label">Age at this read</dt>
            <dd className="fact-value evidence">
              {typeof selected.bulletin_age_days === 'number' ? selected.bulletin_age_days + ' days' : NOT_RECORDED}
            </dd>
          </div>
          <div className="fact-row">
            <dt className="module-fact-label">Day inspected</dt>
            <dd className="fact-value evidence">{dayIndex === null ? 'the day covering today' : 'day ' + dayIndex}</dd>
          </div>
        </dl>

        <div className="inspector-days">
          {days.length ? days.map(day => {
            const colour = statedColour(day);
            const covers = dayIndex === null ? day.is_today === true : day.day === dayIndex;
            return (
              <div className="inspector-day" key={'day-' + String(day.day)} data-today={covers ? 'true' : 'false'} data-day={day.day}>
                <span className="inspector-day-when">{dayWhen(day)}</span>
                <ColourTag colour={colour} text={day.colour || 'colour not stated'} />
                <span className="inspector-day-text">
                  {dayWording(day)}
                  {covers ? <strong> · covers the day inspected</strong> : null}
                </span>
              </div>
            );
          }) : (
            <p className="module-note m-0">
              This district's row states no published day, so there is no day line to show. The row itself is in
              the read: edition {orNot(selected.bulletin_date, NOT_RECORDED)}.
            </p>
          )}
        </div>

        {!today ? (
          <p className="module-note m-0">
            No published day covers the day being inspected here, so the figure draws this district as an outline.
          </p>
        ) : null}

        <div className="inspector-actions">
          <a className="btn" href={warningsHref(name)}>
            <ShieldAlert size={14} aria-hidden="true" />
            Open in Warnings
            <ArrowUpRight size={13} aria-hidden="true" />
          </a>
          <a className="btn btn-primary" href={askHref('What does the published warning say for ' + name + (selected.state ? ', ' + selected.state : '') + ' today?')}>
            <MessageSquare size={14} aria-hidden="true" />
            Ask about this district
          </a>
          <Button size="sm" variant="ghost" onClick={() => onSelect('')}>Clear selection</Button>
        </div>
      </section>
    );
  }

  const byState = new Map<string, { key: string; name: string; colour: string | null; edition: string | null }[]>();
  rows.forEach(row => {
    const state = row.state || 'state not stated in this read';
    const day = dayIndex === null ? (row.days || []).find(entry => entry.is_today === true) || null : (row.days || []).find(entry => entry.day === dayIndex) || null;
    const list = byState.get(state) || [];
    list.push({ key: row.key || '', name: row.district || 'name not stated', colour: statedColour(day), edition: row.bulletin_date || null });
    byState.set(state, list);
  });
  const states = Array.from(byState.entries()).map(([state, districts]) => {
    const coloured = districts.filter(district => district.colour);
    const tally = new Map<string, number>();
    coloured.forEach(district => { if (district.colour) tally.set(district.colour, (tally.get(district.colour) || 0) + 1); });
    const top = Array.from(tally.entries()).sort((left, right) => (SEVERITY[left[0]] ?? 9) - (SEVERITY[right[0]] ?? 9) || right[1] - left[1])[0];
    return { state, total: districts.length, coloured: coloured.length, top: top ? top[0] : null, topCount: top ? top[1] : 0 };
  }).sort((left, right) => right.coloured - left.coloured || left.state.localeCompare(right.state));

  if (statePick) {
    const list = (byState.get(statePick) || []).slice().sort((left, right) => (SEVERITY[left.colour || 'unset'] ?? 9) - (SEVERITY[right.colour || 'unset'] ?? 9) || left.name.localeCompare(right.name));
    return (
      <section className="glass-soft inspector p-3" data-testid="today-inspector-state">
        <div className="inspector-head">
          <div className="min-w-0">
            <p className="eyebrow m-0">State inspector</p>
            <h3 className="inspector-title mt-1">{statePick}</h3>
            <p className="module-note m-0">
              {list.length ? count(list.length, 'district') + ' in this read belong to this state' : 'No district in this read states this state'}.
              Choose one to read its days, or clear the state filter to see every state again.
            </p>
          </div>
        </div>
        <div className="inspector-list">
          {list.map(entry => (
            <button
              key={entry.key || entry.name}
              type="button"
              className="inspector-row"
              onClick={() => entry.key && onSelect(entry.key)}
              disabled={!entry.key}
            >
              <span className="min-w-0 truncate">{entry.name}</span>
              <ColourTag colour={entry.colour} text={entry.colour || 'no colour'} />
              <span className="inspector-count">{entry.edition ? entry.edition.slice(0, 10) : '—'}</span>
            </button>
          ))}
        </div>
        <div className="inspector-actions">
          <Button size="sm" variant="ghost" onClick={() => onState('')}>Clear the state filter</Button>
        </div>
      </section>
    );
  }

  return (
    <section className="glass-soft inspector p-3" data-testid="today-inspector-states">
      <div className="inspector-head">
        <div className="min-w-0">
          <p className="eyebrow m-0">States in this read</p>
          <h3 className="inspector-title mt-1">Where the published colours are</h3>
          <p className="module-note m-0">
            Ordered by how many districts published a colour for the day being inspected. Choosing a state filters
            the figure and lists that state's districts. A district with no row is still drawn as an outline and
            can be selected on the figure.
          </p>
        </div>
      </div>
      <div className="inspector-list">
        {states.slice(0, 40).map(entry => (
          <button key={entry.state} type="button" className="inspector-row" onClick={() => onState(entry.state)}>
            <span className="min-w-0 truncate">{entry.state}</span>
            {entry.top ? <ColourTag colour={entry.top} text={entry.top} /> : <ColourTag colour={null} text="no colour" />}
            <span className="inspector-count">{entry.coloured} / {entry.total}</span>
          </button>
        ))}
      </div>
      {states.length > 40 ? (
        <p className="module-note m-0">Showing 40 of {states.length} states this read returned, ordered by published colours.</p>
      ) : null}
      <div className="inspector-actions">
        <a className="btn" href={warningsHref('')}>
          <ShieldAlert size={14} aria-hidden="true" />
          Open the warnings surface
          <ArrowUpRight size={13} aria-hidden="true" />
        </a>
      </div>
    </section>
  );
}
