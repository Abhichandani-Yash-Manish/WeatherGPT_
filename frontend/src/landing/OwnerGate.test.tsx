/* The owner gate's interactions, checked against a browser-shaped environment: what it says before it asks,
   what it refuses, what it unlocks and what forgetting it leaves behind. These test the interface lock, which
   is all the gate is: it protects nothing on disk and the checks below do not claim that it does. */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { OwnerGate } from './OwnerGate';
import { forgetOwner, hasOwnerVerifier, isGateOpen, isSkipped, OWNER_KEY } from './owner';

const PASSPHRASE = 'a-long-enough-passphrase';

async function setPassphrase() {
  await userEvent.click(screen.getByRole('button', { name: 'Set a passphrase' }));
  await userEvent.type(screen.getByLabelText('Passphrase'), PASSPHRASE);
  await userEvent.type(screen.getByLabelText('Enter it again'), PASSPHRASE);
  await userEvent.click(screen.getByTestId('gate-create'));
  await waitFor(() => expect(hasOwnerVerifier()).toBe(true));
}

describe('the owner gate', () => {
  beforeEach(() => {
    try {
      window.localStorage.clear();
    } catch {
      /* storage is optional */
    }
    forgetOwner();
  });

  it('explains what it is and what it is not before asking for anything', () => {
    render(<OwnerGate onOpen={vi.fn()} onSkip={vi.fn()} onEnter={vi.fn()} />);
    expect(screen.getByText(/not authentication/i)).toBeInTheDocument();
    expect(screen.getByText(/not encryption/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Set a passphrase' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Skip - keep the workspace open/ })).toBeInTheDocument();
    expect(hasOwnerVerifier()).toBe(false);
  });

  it('skipping leaves the workspace exactly as open as it was', async () => {
    const onSkip = vi.fn();
    render(<OwnerGate onOpen={vi.fn()} onSkip={onSkip} onEnter={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: /Skip - keep the workspace open/ }));
    expect(isSkipped()).toBe(true);
    expect(isGateOpen()).toBe(true);
    expect(hasOwnerVerifier()).toBe(false);
    expect(onSkip).toHaveBeenCalled();
  });

  it('refuses a passphrase that is too short, and sets nothing', async () => {
    render(<OwnerGate onOpen={vi.fn()} onSkip={vi.fn()} onEnter={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: 'Set a passphrase' }));
    await userEvent.type(screen.getByLabelText('Passphrase'), 'short');
    await userEvent.type(screen.getByLabelText('Enter it again'), 'short');
    await userEvent.click(screen.getByTestId('gate-create'));
    await waitFor(() => expect(screen.getByTestId('gate-state')).toHaveTextContent(/characters|at least/i));
    expect(hasOwnerVerifier()).toBe(false);
  });

  it('refuses a mismatch between the two entries, and sets nothing', async () => {
    render(<OwnerGate onOpen={vi.fn()} onSkip={vi.fn()} onEnter={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: 'Set a passphrase' }));
    await userEvent.type(screen.getByLabelText('Passphrase'), PASSPHRASE);
    await userEvent.type(screen.getByLabelText('Enter it again'), PASSPHRASE + 'x');
    await userEvent.click(screen.getByTestId('gate-create'));
    await waitFor(() => expect(screen.getByTestId('gate-state')).toHaveTextContent(/do not match|differ|same/i));
    expect(hasOwnerVerifier()).toBe(false);
  });

  it('unlocks with the passphrase it was given, and counts a wrong one as an attempt', async () => {
    const first = render(<OwnerGate onOpen={vi.fn()} onSkip={vi.fn()} onEnter={vi.fn()} />);
    await setPassphrase();
    expect(isGateOpen()).toBe(true);
    first.unmount();

    const onOpen = vi.fn();
    render(<OwnerGate onOpen={onOpen} onSkip={vi.fn()} onEnter={vi.fn()} />);
    await userEvent.type(screen.getByLabelText('Passphrase'), 'the-wrong-passphrase');
    await userEvent.click(screen.getByTestId('gate-unlock-button'));
    await waitFor(() => expect(screen.getByTestId('gate-state')).toHaveTextContent(/attempt/i));
    expect(onOpen).not.toHaveBeenCalled();
  });

  it('accepts the passphrase it stored, and never stores the passphrase itself', async () => {
    const first = render(<OwnerGate onOpen={vi.fn()} onSkip={vi.fn()} onEnter={vi.fn()} />);
    await setPassphrase();
    const stored = String(window.localStorage.getItem(OWNER_KEY));
    expect(stored).not.toContain(PASSPHRASE);
    expect(JSON.parse(stored).v).toBe(1);
    first.unmount();

    const onOpen = vi.fn();
    render(<OwnerGate onOpen={onOpen} onSkip={vi.fn()} onEnter={vi.fn()} />);
    await userEvent.type(screen.getByLabelText('Passphrase'), PASSPHRASE);
    await userEvent.click(screen.getByTestId('gate-unlock-button'));
    await waitFor(() => expect(onOpen).toHaveBeenCalled());
  });

  it('forgets the verifier and says the workspace is open to anyone at this machine', async () => {
    const first = render(<OwnerGate onOpen={vi.fn()} onSkip={vi.fn()} onEnter={vi.fn()} />);
    await setPassphrase();
    first.unmount();
    render(<OwnerGate onOpen={vi.fn()} onSkip={vi.fn()} onEnter={vi.fn()} />);
    await userEvent.click(screen.getByTestId('gate-forget'));
    await waitFor(() => expect(hasOwnerVerifier()).toBe(false));
    expect(isGateOpen()).toBe(false);
    expect(screen.getByRole('button', { name: 'Set a passphrase' })).toBeInTheDocument();
  });
});
