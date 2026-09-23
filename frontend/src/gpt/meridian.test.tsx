import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AnswerEvidence } from '../chat/AnswerEvidence';
import userEvent from '@testing-library/user-event';
import { Composer } from './Composer';
import { useAtmosphere } from './atmosphere';
import { currentGroundTheme } from './orb';

afterEach(() => { cleanup(); localStorage.removeItem('weathergpt.atmosphere'); delete document.documentElement.dataset.design; });

describe('Meridian preserves the conversation contracts', () => {
  it('retains separate editions and receipts from the same source in the owning answer', () => {
    render(<AnswerEvidence citations={[
      { id: 'old-edition', source_id: 'S3', provider: 'Publisher', product: 'Bulletin', page: 2, sha256: 'a'.repeat(64), retrieved_at_utc: '2026-09-21T05:00:00Z', url: 'https://example.org/old' },
      { id: 'new-edition', source_id: 'S3', provider: 'Publisher', product: 'Bulletin', page: 8, sha256: 'b'.repeat(64), retrieved_at_utc: '2026-09-22T05:00:00Z', url: 'https://example.org/new' },
    ]} />);
    const margin = screen.getByRole('complementary', { name: 'Evidence for this answer' });
    expect(margin.querySelectorAll('details')).toHaveLength(1);
    expect(margin.querySelector('.g-fold-count')).toHaveTextContent('1');
    fireEvent.click(margin.querySelector('summary')!);
    expect(within(margin).getByText('old-edition · page 2')).toBeInTheDocument();
    expect(within(margin).getByText('new-edition · page 8')).toBeInTheDocument();
    expect(within(margin).getByTitle('a'.repeat(64))).toBeInTheDocument();
    expect(within(margin).getByTitle('b'.repeat(64))).toBeInTheDocument();
    expect(within(margin).getAllByRole('link').map(a => a.getAttribute('href'))).toEqual(['https://example.org/old', 'https://example.org/new']);
  });

  it('states missing source metadata and never offers a non-web citation as a link', () => {
    const { rerender, container } = render(<AnswerEvidence citations={[{ id: 'c1', source_id: 'S3', url: 'javascript:alert(1)' }]} />);
    fireEvent.click(container.querySelector('summary')!);
    expect(screen.getByText('Read time not recorded')).toBeInTheDocument();
    expect(screen.queryByRole('link')).toBeNull();
    rerender(<AnswerEvidence citations={[]} />);
    expect(screen.queryByRole('complementary')).toBeNull();
  });

  it('does not submit an IME confirmation, but ordinary Enter still asks', () => {
    const send = vi.fn();
    render(<Composer draft="અમદાવાદમાં વરસાદ?" onDraft={() => {}} onSend={send} onStop={() => {}} busy={false} language="gu" />);
    const input = screen.getByLabelText('Your question');
    fireEvent.keyDown(input, { key: 'Enter', isComposing: true });
    fireEvent.keyDown(input, { key: 'Enter', keyCode: 229 });
    expect(send).not.toHaveBeenCalled();
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(send).toHaveBeenCalledExactlyOnceWith('અમદાવાદમાં વરસાદ?');
  });

  it('remembers a paused atmosphere without affecting a running request', () => {
    function Control() {
      const atmosphere = useAtmosphere();
      return <button onClick={atmosphere.toggle} aria-pressed={atmosphere.enabled}>{atmosphere.running ? 'Moving' : 'Still'}</button>;
    }
    const { unmount } = render(<Control />);
    fireEvent.click(screen.getByRole('button', { name: 'Moving' }));
    expect(screen.getByRole('button', { name: 'Still' })).toHaveAttribute('aria-pressed', 'false');
    unmount();
    render(<Control />);
    expect(screen.getByRole('button', { name: 'Still' })).toBeInTheDocument();
  });

  it('uses the light activity mark even at night in the selected light interface', () => {
    document.documentElement.dataset.design = 'meridian';
    document.documentElement.dataset.hour = 'night';
    expect(currentGroundTheme()).toBe('light');
    delete document.documentElement.dataset.hour;
  });
});


describe('composer language control', () => {
  it('selects a real answer language with the keyboard and dismisses with Escape', async () => {
    const user = userEvent.setup();
    const change = vi.fn();
    render(<Composer draft="" onDraft={() => {}} onSend={() => {}} onStop={() => {}} busy={false} language=""
      onLanguage={change} languages={[{code: 'en', label: 'English'}, {code: 'hi', label: 'Hindi'}]} />);
    const trigger = await screen.findByRole('button', {name: 'Answer language'});
    await user.click(trigger);
    await user.keyboard('h{Enter}');
    expect(change).toHaveBeenCalledWith('hi');
    await user.click(trigger);
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('listbox')).toBeNull();
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it('states a failed language read and offers a working retry', async () => {
    const user = userEvent.setup();
    const retry = vi.fn();
    render(<Composer draft="" onDraft={() => {}} onSend={() => {}} onStop={() => {}} busy={false} language=""
      onLanguage={() => {}} languageState="error" onRetryLanguages={retry} />);
    expect(await screen.findByRole('button', {name: 'Answer language'})).toBeDisabled();
    expect(screen.getByText('Languages unavailable')).toBeInTheDocument();
    await user.click(screen.getByRole('button', {name: 'Retry languages'}));
    expect(retry).toHaveBeenCalledOnce();
  });
});
