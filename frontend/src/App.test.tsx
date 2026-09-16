import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from './App';

describe('the R0 shell', () => {
  it('renders the chat-first landing surface with one question box', async () => {
    render(<App />);
    const box = screen.getByLabelText('Your question');
    await userEvent.type(box, 'Will it rain in Surat tomorrow morning?');
    expect(box).toHaveValue('Will it rain in Surat tomorrow morning?');
    expect(screen.getByRole('button', { name: 'Ask' })).toBeInTheDocument();
  });

  it('says the build is groundwork rather than pretending to answer', () => {
    render(<App />);
    expect(screen.getByTestId('r0-note')).toHaveTextContent(/not wired in this build yet/i);
  });
});
