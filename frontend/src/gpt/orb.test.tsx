/* The orb in the wait: its state comes from the engine, and its ink comes from the ground.
   ============================================================================
   Two defaults of the library would be wrong here, so both are held by a check rather than by care:

   1. its state is a verb. The product may not show a word for something the engine did not state, so the
      mapping is asserted to answer EVERY stage the engine can state, and an unrecognised stage is asserted
      to fall back to the neutral one rather than to a guess;
   2. its theme is the operating system's, and this product's ground is the hour's. The two disagree exactly
      when it matters - a dark OS on the daybreak ground - so the theme is asserted against the hour.

   The library's own registry is the source of truth for the first: a state that has no drawing behind it in
   thinking-orbs fails here rather than rendering an empty canvas in a reader's browser. */

import { render, screen, cleanup } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { STATE_TO_MODE } from 'thinking-orbs';
import type { Working } from '../chat/model';
import { ENGINE_STAGES, LIGHT_GROUND_HOURS, ORB_FALLBACK, STAGE_ORB, currentGroundTheme, groundThemeFor, orbStateFor } from './orb';
import { WorkingTurn } from './WorkingTurn';

/* The real orb draws on a canvas, which jsdom has no 2D context for; the library returns early rather than
   throwing, but nothing about the mapping would be visible in a canvas anyway. So the component is replaced by
   a canvas that states the props it was handed - which is exactly what these checks are about. */
vi.mock('thinking-orbs', async () => {
  const actual = await vi.importActual<typeof import('thinking-orbs')>('thinking-orbs');
  return {
    ...actual,
    ThinkingOrb: (props: { state?: string; theme?: string; paused?: boolean; size?: number }) => (
      <canvas
        data-testid="orb"
        data-state={props.state}
        data-theme={props.theme}
        data-paused={String(Boolean(props.paused))}
        data-size={String(props.size)}
      />
    ),
  };
});

const working = (over: Partial<Working> = {}): Working => ({
  key: 'turn-1', requestId: 'req-1', question: 'Will it rain in Surat tomorrow?', startedAt: 1_758_000_000_000,
  preview: null, previewFailed: null, progress: null, stopRequested: false, stopDetail: null, ...over,
});

afterEach(() => {
  cleanup();
  delete document.documentElement.dataset.hour;
});

describe('the orb says what the engine said, or nothing in particular', () => {
  it('answers every stage the engine can state', () => {
    /* The check with teeth: the day the engine states a stage this table has not answered, this fails. A
       fallback would let a new stage be drawn as "working" for ever, which is the silent version of guessing. */
    const unanswered = ENGINE_STAGES.filter(stage => !STAGE_ORB[stage]);
    expect(unanswered, 'the engine states a stage the orb has no answer for: ' + unanswered.join(', ')).toEqual([]);
  });

  it('names only states this library can actually draw', () => {
    const undrawable = Object.entries(STAGE_ORB).filter(([, state]) => !STATE_TO_MODE[state]);
    expect(undrawable, 'no drawing behind: ' + JSON.stringify(undrawable)).toEqual([]);
  });

  it('shows the neutral state for a stage this build does not know, rather than a guess', () => {
    expect(orbStateFor('summarising')).toBe(ORB_FALLBACK);
    expect(orbStateFor('')).toBe(ORB_FALLBACK);
    expect(orbStateFor(null)).toBe(ORB_FALLBACK);
    expect(orbStateFor(undefined)).toBe(ORB_FALLBACK);
  });

  it('treats stopping at a task boundary as still, not as working', () => {
    /* The engine stops at a boundary; an orb that kept orbiting would say work was continuing. */
    expect(orbStateFor('task boundary')).toBe('breathing');
    expect(orbStateFor('task boundary')).not.toBe(ORB_FALLBACK);
  });

  it('is read from the engine\u2019s stage in the wait, and freezes when the reader has asked to stop', () => {
    const { container } = render(
      <WorkingTurn working={working()} current="retrieving" stages={['retrieving']} firstReading={null} queueLine="" />,
    );
    const orb = screen.getByTestId('orb');
    expect(orb.dataset.state).toBe('searching');
    expect(orb.dataset.size).toBe('20');
    expect(orb.dataset.paused).toBe('false');
    /* The canvas carries no label of its own: the stage word beside it is the live region, so a screen reader
       hears the stage once. */
    expect(container.querySelector('.g-orb')?.getAttribute('aria-hidden')).toBe('true');
    /* The three hand-rolled dots are gone, and this is the line that notices if they come back. */
    expect(container.querySelector('.g-dots')).toBeNull();
  });

  it('freezes on the frame it reached when the reader asks it to stop', () => {
    render(<WorkingTurn working={working({ stopRequested: true })} current="retrieving" stages={['retrieving']} firstReading={null} queueLine="" />);
    expect(screen.getByTestId('orb').dataset.paused).toBe('true');
  });
});

describe('the orb\u2019s ink follows the ground, which is the hour\u2019s and not the operating system\u2019s', () => {
  it('is light only on the two hours whose ground is light', () => {
    /* This list is not a preference: it is the two selectors tokens.css keys on. */
    expect(LIGHT_GROUND_HOURS).toEqual(['daybreak', 'noon']);
    expect(groundThemeFor('daybreak')).toBe('light');
    expect(groundThemeFor('noon')).toBe('light');
    expect(groundThemeFor('golden')).toBe('dark');
    expect(groundThemeFor('night')).toBe('dark');
  });

  it('reads a missing or unknown hour as the stylesheet\u2019s own default', () => {
    expect(groundThemeFor(null)).toBe('dark');
    expect(groundThemeFor(undefined)).toBe('dark');
    expect(groundThemeFor('the gloaming')).toBe('dark');
  });

  it('is taken from the attribute that painted the ground, not from the clock', () => {
    expect(currentGroundTheme()).toBe('dark');
    document.documentElement.dataset.hour = 'daybreak';
    expect(currentGroundTheme()).toBe('light');
    render(<WorkingTurn working={working()} current="started" stages={['started']} firstReading={null} queueLine="" />);
    expect(screen.getByTestId('orb').dataset.theme).toBe('light');
  });
});
