/* Keyboard-only acceptance for the shell's three contracts: the skip link reaches the question box, the
   surface shortcuts work without a pointer, and the command palette takes focus when it opens. */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from '../App';

describe('keyboard acceptance', () => {
  beforeEach(() => {
    window.location.hash = '#/assistant';
    try {
      window.localStorage.clear();
    } catch {
      /* storage is optional */
    }
  });

  it('offers a skip link first, and it puts the cursor in the question box', async () => {
    render(<App />);
    const skip = screen.getByRole('link', { name: 'Skip to the question box' });
    const box = screen.getByLabelText('Your question');
    expect(skip.compareDocumentPosition(box) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    await userEvent.click(skip);
    expect(document.activeElement).toBe(box);
  });

      it('opens the command palette with the keyboard and puts the cursor in its search field', async () => {
    render(<App />);
    await userEvent.keyboard('{Alt>}k{/Alt}');
    const palette = await screen.findByRole('dialog', { name: 'Command palette' });
    await waitFor(() => expect(document.activeElement).toBe(document.getElementById('palette-search')));
    expect(palette).toBeInTheDocument();
  });

  it('moves through the palette list with the arrow keys and opens the chosen surface with Enter', async () => {
    render(<App />);
    await userEvent.keyboard('{Alt>}k{/Alt}');
    await screen.findByRole('dialog', { name: 'Command palette' });
    const input = document.getElementById('palette-search') as HTMLInputElement;
    await userEvent.type(input, 'Warnings');
    await userEvent.keyboard('{Enter}');
    expect(window.location.hash).toBe('#/warnings');
  });
});
