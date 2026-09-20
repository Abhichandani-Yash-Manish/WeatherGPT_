import { useEffect, useState, type FormEvent } from 'react';
import { createOwner, forgetOwner, isGateOpen, openGate, readOwnerVerifier, skipGate, verifyOwner } from './owner';

/* The owner gate.
   ============================================================================
   The workspace runs on loopback with a per-process session token and no account system. This is not a login
   screen and must not read like one: it is a passphrase check kept in this browser, and every sentence on it
   says what it is, what it is not, and what it stores. The same wording that keeps the interface honest keeps
   this honest too — the gate never claims to have secured anything.

   Props:
   - onOpen  the gate was passed for this browser (a passphrase was set, or an unlock verified);
   - onSkip  the reader chose to leave the workspace open, exactly as it is today;
   - onEnter the workspace when this session's gate is already open.

   The page is left to own the h1 and the landmarks, so this renders a labelled section. */

const MIN_PASSPHRASE = 8;
const ATTEMPT_LIMIT = 5;
const PAUSE_SECONDS = 30;
const ATTEMPT_WORDS = ['no attempts', 'one attempt', 'two attempts', 'three attempts', 'four attempts', 'five attempts'];

type Mode = 'explain' | 'choose' | 'unlock';

export function OwnerGate({ onOpen, onSkip, onEnter }: { onOpen: () => void; onSkip: () => void; onEnter: () => void }) {
  const [openAtMount] = useState(() => isGateOpen());
  const [mode, setMode] = useState<Mode>(() => (readOwnerVerifier() ? 'unlock' : 'explain'));
  const [passphrase, setPassphrase] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [attempt, setAttempt] = useState('');
  const [working, setWorking] = useState(false);
  const [failures, setFailures] = useState(0);
  const [pausedUntil, setPausedUntil] = useState<number | null>(null);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [message, setMessage] = useState(
    'Nothing has been asked for yet. Read what this gate is and what it is not, then choose.',
  );

  const paused = pausedUntil !== null;

  /* The pause counts down visibly and then releases on its own; local only, and a courtesy rather than a
     security control, which the countdown says out loud. */
  useEffect(() => {
    if (pausedUntil === null) return;
    const tick = () => {
      const left = Math.max(0, Math.ceil((pausedUntil - Date.now()) / 1000));
      setSecondsLeft(left);
      if (left === 0) {
        setPausedUntil(null);
        setFailures(0);
        setMessage('The pause is over. You can try the passphrase again.');
      }
    };
    tick();
    const timer = window.setInterval(tick, 1000);
    return () => window.clearInterval(timer);
  }, [pausedUntil]);

  function backToExplain() {
    setMode('explain');
    setPassphrase('');
    setConfirmation('');
    setAttempt('');
    setMessage('Nothing has been asked for yet. Read what this gate is and what it is not, then choose.');
  }

  async function submitPassphrase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (passphrase.length < MIN_PASSPHRASE) {
      setMessage('A passphrase here must be at least eight characters. Nothing has been stored.');
      return;
    }
    if (passphrase !== confirmation) {
      setMessage('The two passphrases do not match. Nothing has been stored.');
      return;
    }
    setWorking(true);
    setMessage('Deriving the verifier in this browser. This takes a moment and nothing is sent anywhere.');
    try {
      await createOwner(passphrase);
      setPassphrase('');
      setConfirmation('');
      setMessage('The verifier is stored in this browser. The passphrase itself was not stored, logged or sent anywhere.');
      onOpen();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'The verifier could not be stored on this machine.');
    } finally {
      setWorking(false);
    }
  }

  async function submitUnlock(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (paused || working) return;
    setWorking(true);
    const verdict = await verifyOwner(attempt);
    setAttempt('');
    if (verdict === 'verified') {
      setWorking(false);
      openGate();
      setMessage('That passphrase matched the verifier in this browser. Nothing was sent anywhere.');
      onOpen();
      return;
    }
    if (verdict === 'no-verifier') {
      setWorking(false);
      setMode('explain');
      setMessage('No verifier can be read in this browser, so no passphrase can be checked here. Set one, or skip.');
      return;
    }
    const next = failures + 1;
    const left = ATTEMPT_LIMIT - next;
    setFailures(next);
    setWorking(false);
    if (left <= 0) {
      setPausedUntil(Date.now() + PAUSE_SECONDS * 1000);
      setSecondsLeft(PAUSE_SECONDS);
      setMessage('That passphrase did not match. The workspace is paused until the countdown below reaches zero.');
      return;
    }
    setMessage(
      'That passphrase did not match. ' + ATTEMPT_WORDS[left] +
        ' left before a thirty-second pause; this count is kept locally in this browser.',
    );
  }

  function forget() {
    forgetOwner();
    setPausedUntil(null);
    setFailures(0);
    backToExplain();
    setMessage('The verifier was removed from this browser. The workspace is now open to anyone at this machine.');
  }

  return (
    <section aria-labelledby="owner-gate-title" className="card max-w-2xl p-5" data-surface="owner-gate">
      {mode === 'explain' ? (
        <>
          <p className="eyebrow">Owner gate · this machine</p>
          <h2 id="owner-gate-title" className="display mt-2">A local passphrase check, and nothing more than that</h2>
          <p className="reading mt-3">
            This gate exists so a shared machine does not show the workspace to whoever sits down at it. It is a
            shoulder-surfing barrier on this machine's screen; the workspace itself is unchanged by it.
          </p>
          {/* `gate-explains` is the class the X1 audit names for this list: the gate describing what it
              stores on this machine — including the name of the key-derivation function, which contains
              digits and is not a value anything read. */}
          <ul className="gate-explains mt-4 space-y-3 text-sm text-ink-soft">
            <li>
              <strong>What it is.</strong> A passphrase whose verifier is derived in this browser and kept in this
              browser's local storage. Nothing about it leaves the machine.
            </li>
            <li>
              <strong>What it is not.</strong> Not authentication, not an account system and not encryption: nothing
              at rest is encrypted, and the workspace files stay as they are.
            </li>
            <li>
              <strong>It does not protect the API.</strong> The workspace server keeps its own per-process session
              token check on every request, with this gate open or closed.
            </li>
            <li>
              <strong>What is stored, and where.</strong> In this browser's local storage: the format version, a
              random salt, the PBKDF2-SHA-256 iteration count and the derived verifier. The passphrase itself is
              never stored, never logged and never sent anywhere.
            </li>
            <li>
              <strong>What it cannot do.</strong> It does not hide anything from the operating system or from anyone
              who reads the workspace's own files, and it is not a security control.
            </li>
          </ul>
          <div className="mt-5 flex flex-wrap gap-3">
            <button
              type="button"
              className="btn btn-primary"
              data-testid="gate-set"
              onClick={() => {
                setMode('choose');
                setMessage('Choose a passphrase of eight characters or more. It is never stored, logged or sent anywhere.');
              }}
            >
              Set a passphrase
            </button>
            <button
              type="button"
              className="btn"
              data-testid="gate-skip"
              onClick={() => {
                skipGate();
                onSkip();
              }}
            >
              Skip - keep the workspace open
            </button>
          </div>
          <p className="mt-3 text-xs text-mute">
            Skipping records one flag in this browser and leaves the workspace exactly as open as it is today.
          </p>
          {openAtMount ? (
            <p className="mt-4 flex flex-wrap items-center gap-3 text-sm">
              <span className="evidence">This session's gate is already open.</span>
              <button type="button" className="btn btn-ghost" data-testid="gate-enter" onClick={onEnter}>
                Enter the workspace
              </button>
            </p>
          ) : null}
        </>
      ) : null}

      {mode === 'choose' ? (
        <form onSubmit={submitPassphrase} data-testid="gate-choose">
          <p className="eyebrow">Owner gate · set a passphrase</p>
          <h2 id="owner-gate-title" className="display mt-2">Set the passphrase for this browser</h2>
          <p className="reading mt-3">
            The passphrase is checked here and stored nowhere. Only a derived verifier is kept, so it cannot be
            recovered from this browser.
          </p>
          <div className="mt-4 flex flex-col gap-3">
            <label className="text-sm" htmlFor="owner-passphrase">
              Passphrase
            </label>
            <input
              id="owner-passphrase"
              type="password"
              autoComplete="new-password"
              className="rounded-card border border-line bg-paper px-3 py-2 text-sm"
              value={passphrase}
              onChange={event => setPassphrase(event.target.value)}
            />
            <label className="text-sm" htmlFor="owner-confirmation">
              Enter it again
            </label>
            <input
              id="owner-confirmation"
              type="password"
              autoComplete="new-password"
              className="rounded-card border border-line bg-paper px-3 py-2 text-sm"
              value={confirmation}
              onChange={event => setConfirmation(event.target.value)}
            />
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <button type="submit" className="btn btn-primary" data-testid="gate-create" disabled={working}>
              Set the passphrase
            </button>
            <button type="button" className="btn btn-ghost" onClick={backToExplain}>
              Back
            </button>
          </div>
        </form>
      ) : null}

      {mode === 'unlock' ? (
        <form onSubmit={submitUnlock} data-testid="gate-unlock">
          <p className="eyebrow">Owner gate · returning visit</p>
          <h2 id="owner-gate-title" className="display mt-2">Enter the passphrase set for this browser</h2>
          <p className="reading mt-3">
            The verifier is in this browser's local storage and the check happens here. Nothing is sent anywhere.
          </p>
          <div className="mt-4 flex flex-col gap-3">
            <label className="text-sm" htmlFor="owner-attempt">
              Passphrase
            </label>
            <input
              id="owner-attempt"
              type="password"
              autoComplete="current-password"
              className="rounded-card border border-line bg-paper px-3 py-2 text-sm"
              value={attempt}
              onChange={event => setAttempt(event.target.value)}
              disabled={paused}
            />
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <button type="submit" className="btn btn-primary" data-testid="gate-unlock-button" disabled={working || paused}>
              Unlock
            </button>
            <button type="button" className="btn btn-ghost" data-testid="gate-forget" onClick={forget}>
              Forget it
            </button>
          </div>
          <p className="mt-3 text-xs text-mute">
            Forgetting removes the verifier from this browser. The workspace is then open to anyone at this machine.
          </p>
        </form>
      ) : null}

      <p className="mt-4 text-sm" aria-live="polite" data-testid="gate-state">
        {message}
      </p>
      {paused ? (
        /* `gate-countdown` is the class the X1 audit names here: the number is the pause this gate imposed
           on itself, and the sentence says in the same breath what it is and is not. */
        <p className="evidence gate-countdown mt-2 text-xs text-mute" data-testid="gate-countdown">
          Paused: {secondsLeft} seconds remaining. Local only: this pause is a courtesy, not a security control.
        </p>
      ) : null}
    </section>
  );
}
