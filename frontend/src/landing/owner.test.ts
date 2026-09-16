import {
  OWNER_KEY,
  SKIP_KEY,
  closeGate,
  createOwner,
  forgetOwner,
  hasOwnerVerifier,
  isGateOpen,
  isSkipped,
  readOwnerVerifier,
  skipGate,
  verifyOwner,
} from './owner';

/* The gate's verifier is kept in this browser's local storage. The harness installs an in-memory storage for
   the environment (src/test/setup.ts); this suite installs a fresh one per test so one test's verifier cannot
   decide the next one's answer, and so it can pose a storage that refuses to be read at all. The module's own
   rules are tested below: a refused read and a hand-edited record both read as "no verifier" rather than
   throwing. */
const PASSPHRASE = 'harbour-fog-41';
const WRONG = 'harbour-fog-42';

function base64(bytes: number): string {
  return btoa(String.fromCharCode(...new Uint8Array(bytes)));
}

function installStorage(): Storage {
  const rows = new Map<string, string>();
  const storage: Storage = {
    get length() {
      return rows.size;
    },
    clear: () => rows.clear(),
    getItem: (key: string) => (rows.has(key) ? (rows.get(key) as string) : null),
    key: (index: number) => Array.from(rows.keys())[index] ?? null,
    removeItem: (key: string) => {
      rows.delete(key);
    },
    setItem: (key: string, value: string) => {
      rows.set(key, String(value));
    },
  };
  Object.defineProperty(window, 'localStorage', { value: storage, configurable: true, writable: true });
  return storage;
}

function blockStorage(): void {
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    get: () => {
      throw new Error('SecurityError: this browser will not hand over local storage');
    },
  });
}

describe('the owner verifier', () => {
  beforeEach(() => {
    installStorage();
  });

  it('derives a verifier for the right passphrase and keeps the passphrase itself out of storage', async () => {
    await createOwner(PASSPHRASE);

    expect(hasOwnerVerifier()).toBe(true);
    const record = readOwnerVerifier();
    expect(record).not.toBeNull();
    expect(record?.v).toBe(1);
    expect(record?.iterations).toBe(600000);
    expect(atob(record?.salt as string)).toHaveLength(16);
    expect(atob(record?.hash as string)).toHaveLength(32);

    await expect(verifyOwner(PASSPHRASE)).resolves.toBe('verified');

    const stored = window.localStorage.getItem(OWNER_KEY) as string;
    expect(stored).not.toContain(PASSPHRASE);
    expect(stored).toContain('"iterations":600000');
  });

  it('refuses a passphrase that does not match the stored verifier', async () => {
    await createOwner(PASSPHRASE);
    await expect(verifyOwner(WRONG)).resolves.toBe('refused');
  });

  it('reports no verifier when nothing is stored', async () => {
    expect(readOwnerVerifier()).toBeNull();
    expect(hasOwnerVerifier()).toBe(false);
    await expect(verifyOwner(PASSPHRASE)).resolves.toBe('no-verifier');
  });

  it('treats a corrupt or hand-edited record as no verifier instead of throwing', async () => {
    const values = [
      'not json at all',
      JSON.stringify({ v: 2, salt: base64(16), iterations: 600000, hash: base64(32) }),
      JSON.stringify({ v: 1, salt: '', iterations: 600000, hash: base64(32) }),
      JSON.stringify({ v: 1, salt: '!!!not base64!!!', iterations: 600000, hash: base64(32) }),
      JSON.stringify({ v: 1, salt: base64(16), iterations: 0, hash: base64(32) }),
      JSON.stringify({ v: 1, salt: base64(16), iterations: 1_000_000_000, hash: base64(32) }),
    ];
    for (const value of values) {
      window.localStorage.setItem(OWNER_KEY, value);
      expect(readOwnerVerifier()).toBeNull();
      expect(hasOwnerVerifier()).toBe(false);
      await expect(verifyOwner(PASSPHRASE)).resolves.toBe('no-verifier');
    }
  });

  it('reads a storage that refuses to hand over its values as no verifier rather than throwing', () => {
    blockStorage();
    expect(() => readOwnerVerifier()).not.toThrow();
    expect(readOwnerVerifier()).toBeNull();
    expect(hasOwnerVerifier()).toBe(false);
    expect(isSkipped()).toBe(false);
    expect(isGateOpen()).toBe(false);
    expect(() => closeGate()).not.toThrow();
    expect(() => forgetOwner()).not.toThrow();
  });

  it('reports a write that the browser refuses instead of pretending the passphrase was set', async () => {
    const rows = new Map<string, string>();
    Object.defineProperty(window, 'localStorage', {
      value: {
        get length() {
          return rows.size;
        },
        clear: () => rows.clear(),
        getItem: () => null,
        key: () => null,
        removeItem: () => {},
        setItem: () => {
          throw new Error('QuotaExceededError: this browser refuses the write');
        },
      } as Storage,
      configurable: true,
      writable: true,
    });
    await expect(createOwner(PASSPHRASE)).rejects.toThrow(/refused to store the verifier/);
    expect(hasOwnerVerifier()).toBe(false);
  });

  it('leaves the workspace open when the reader skips the gate', () => {
    expect(isGateOpen()).toBe(false);
    skipGate();
    expect(isSkipped()).toBe(true);
    expect(isGateOpen()).toBe(true);
    expect(window.localStorage.getItem(SKIP_KEY)).toBe('true');
    closeGate();
    expect(isGateOpen()).toBe(false);
  });

  it('forgets the verifier and returns to the first-run state', async () => {
    await createOwner(PASSPHRASE);
    expect(hasOwnerVerifier()).toBe(true);
    forgetOwner();
    expect(readOwnerVerifier()).toBeNull();
    expect(hasOwnerVerifier()).toBe(false);
    expect(isGateOpen()).toBe(false);
    expect(isSkipped()).toBe(false);
    await expect(verifyOwner(PASSPHRASE)).resolves.toBe('no-verifier');
  });
});
