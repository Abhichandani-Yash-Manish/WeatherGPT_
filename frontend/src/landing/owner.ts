/* The owner gate's local verifier.
   ============================================================================
   The workspace runs on loopback behind a per-process session token. There is no account system, nothing is
   encrypted at rest, and this module is not an authentication mechanism: it derives a passphrase verifier in
   the browser (PBKDF2-SHA-256 over a random salt) and keeps it in this browser's local storage, so a shared
   machine does not show the workspace to whoever sits down at it. It gates the interface only; the API keeps
   its own token check either way.

   Three rules hold here:
   1. The passphrase itself is never stored, never logged and never sent anywhere. Only {v, salt, iterations,
      hash} is written, with base64 values.
   2. Every storage read is wrapped. A browser in private mode, a blocked storage or a hand-edited record
      reads as "no verifier" instead of throwing, so the gate can always say what state it is in.
   3. A write that the browser refuses is reported to the caller rather than swallowed: claiming a passphrase
      was set when nothing was stored would be a lie about the only thing this gate does. */

export type OwnerVerifier = { v: 1; salt: string; iterations: number; hash: string };

export const OWNER_KEY = 'weathergpt.owner.v1';
export const SKIP_KEY = 'weathergpt.owner.skip';
export const OPEN_KEY = 'weathergpt.owner.open';

const SALT_BYTES = 16;
const KEY_BITS = 256;
const ITERATIONS = 600000;
/* The iteration count is read back from storage, so it is bounded before it is run: a corrupt or hand-edited
   record is refused as no verifier rather than turning one unlock into an unbounded wait. */
const ITERATION_LIMIT = 5000000;

function store(): Storage | null {
  try {
    const candidate = window.localStorage;
    if (!candidate || typeof candidate.getItem !== 'function' || typeof candidate.setItem !== 'function') return null;
    return candidate;
  } catch {
    /* A browser that refuses to hand over its storage reads as no storage, never as a crash. */
    return null;
  }
}

function readRaw(key: string): string | null {
  try {
    const value = store()?.getItem(key);
    return typeof value === 'string' && value ? value : null;
  } catch {
    return null;
  }
}

function writeRaw(key: string, value: string): boolean {
  try {
    const target = store();
    if (!target) return false;
    target.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}

function removeRaw(key: string): void {
  try {
    store()?.removeItem(key);
  } catch {
    /* A storage that refuses the removal keeps the value; a reader still sees the state it can read. */
  }
}

function toBase64(bytes: Uint8Array): string {
  let binary = '';
  for (let index = 0; index < bytes.length; index += 1) binary += String.fromCharCode(bytes[index]);
  return btoa(binary);
}

function fromBase64(value: string): Uint8Array<ArrayBuffer> {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return bytes;
}

/* Two byte strings are compared without an early exit, so a failed attempt does not say where it diverged. */
function sameBytes(left: Uint8Array, right: Uint8Array): boolean {
  if (left.length !== right.length) return false;
  let difference = 0;
  for (let index = 0; index < left.length; index += 1) difference |= left[index] ^ right[index];
  return difference === 0;
}

async function derive(passphrase: string, salt: Uint8Array<ArrayBuffer>, iterations: number): Promise<Uint8Array> {
  const subtle = window.crypto?.subtle;
  if (!subtle) throw new Error('This browser exposes no WebCrypto implementation, so a passphrase verifier cannot be derived here.');
  const material = await subtle.importKey('raw', new TextEncoder().encode(passphrase), 'PBKDF2', false, ['deriveBits']);
  const bits = await subtle.deriveBits({ name: 'PBKDF2', hash: 'SHA-256', salt, iterations }, material, KEY_BITS);
  return new Uint8Array(bits);
}

export function readOwnerVerifier(): OwnerVerifier | null {
  const raw = readRaw(OWNER_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<OwnerVerifier> | null;
    if (!parsed || typeof parsed !== 'object' || parsed.v !== 1) return null;
    if (typeof parsed.salt !== 'string' || typeof parsed.hash !== 'string' || !parsed.salt || !parsed.hash) return null;
    const iterations = Number(parsed.iterations);
    if (!Number.isInteger(iterations) || iterations < 1 || iterations > ITERATION_LIMIT) return null;
    /* Both values are decoded on the read, so a corrupt record is refused here rather than at a comparison. */
    fromBase64(parsed.salt);
    fromBase64(parsed.hash);
    return { v: 1, salt: parsed.salt, iterations, hash: parsed.hash };
  } catch {
    return null;
  }
}

export function hasOwnerVerifier(): boolean {
  return readOwnerVerifier() !== null;
}

export async function createOwner(passphrase: string): Promise<OwnerVerifier> {
  const salt = new Uint8Array(SALT_BYTES);
  window.crypto.getRandomValues(salt);
  const hash = await derive(passphrase, salt, ITERATIONS);
  const record: OwnerVerifier = { v: 1, salt: toBase64(salt), iterations: ITERATIONS, hash: toBase64(hash) };
  if (!writeRaw(OWNER_KEY, JSON.stringify(record))) {
    throw new Error('This browser refused to store the verifier in local storage, so no passphrase was set and the workspace is unchanged.');
  }
  openGate();
  return record;
}

export async function verifyOwner(passphrase: string): Promise<'verified' | 'refused' | 'no-verifier'> {
  const verifier = readOwnerVerifier();
  if (!verifier) return 'no-verifier';
  try {
    const derived = await derive(passphrase, fromBase64(verifier.salt), verifier.iterations);
    /* A derived value that cannot be computed (no WebCrypto) is reported as nothing to check against,
       never as a match. */
    return sameBytes(derived, fromBase64(verifier.hash)) ? 'verified' : 'refused';
  } catch {
    return 'no-verifier';
  }
}

export function isSkipped(): boolean {
  return readRaw(SKIP_KEY) === 'true';
}

/* Skipping is recorded and leaves the workspace open, which is exactly the state it is in today. */
export function skipGate(): void {
  writeRaw(SKIP_KEY, 'true');
  openGate();
}

export function isGateOpen(): boolean {
  return readRaw(OPEN_KEY) === 'true';
}

export function openGate(): void {
  writeRaw(OPEN_KEY, 'true');
}

export function closeGate(): void {
  removeRaw(OPEN_KEY);
}

/* Forgetting the verifier returns the browser to the first-run state: no verifier, no skip, no open gate. */
export function forgetOwner(): void {
  removeRaw(OWNER_KEY);
  removeRaw(SKIP_KEY);
  removeRaw(OPEN_KEY);
}
