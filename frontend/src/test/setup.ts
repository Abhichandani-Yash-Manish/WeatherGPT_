/* The interface's own language. main.tsx initialises i18next at the entry point, and a test renders a
   component rather than the entry, so without this every t() call returns its key and a spec looking for
   "Your question" finds "composer.label" instead. Initialising it here is what the app does, not a
   convenience for the tests: the catalogues are part of the interface, not a fixture. */
import '../i18n';

import '@testing-library/jest-dom/vitest';
import { afterAll, afterEach, beforeAll, vi } from 'vitest';
import { transferableAbortController } from 'node:util';
import { server } from './msw';

/* jsdom hands out its own AbortSignal, and the fetch implementation the test environment uses refuses
   any signal that is not a real one: "Expected signal (\"AbortSignal {}\") to be an instance of
   AbortSignal". The product code is right to pass a signal, so the harness supplies the class the fetch
   implementation accepts rather than the product weakening its cancellation. Measured: with this stub the
   same request answers 200 through msw. */
if (typeof transferableAbortController === 'function') {
  class NodeAbortController {
    private inner = transferableAbortController();
    get signal(): AbortSignal {
      return this.inner.signal as AbortSignal;
    }
    abort(reason?: unknown): void {
      this.inner.abort(reason as never);
    }
  }
  vi.stubGlobal('AbortController', NodeAbortController);
}

/* This Node build ships no localStorage unless a file is named, and the product remembers a register and a
   theme across visits. The harness provides an in-memory storage so that path is exercised rather than
   skipped, exactly as a browser would exercise it. */
if (!('localStorage' in window) || !window.localStorage) {
  const store = new Map<string, string>();
  const memory: Storage = {
    get length() {
      return store.size;
    },
    clear: () => store.clear(),
    getItem: (key: string) => (store.has(key) ? String(store.get(key)) : null),
    key: (index: number) => Array.from(store.keys())[index] ?? null,
    removeItem: (key: string) => void store.delete(key),
    setItem: (key: string, value: string) => void store.set(key, String(value)),
  };
  Object.defineProperty(window, 'localStorage', { configurable: true, value: memory });
}

/* jsdom implements no modal dialog, and the command palette asks the browser for one rather than
   reimplementing focus handling. The harness adds the two methods a browser has. */
if (typeof HTMLDialogElement !== 'undefined') {
  const proto = HTMLDialogElement.prototype as HTMLDialogElement & { showModal?: () => void };
  if (!proto.showModal) {
    proto.showModal = function showModal(this: HTMLDialogElement) {
      this.setAttribute('open', '');
    };
  }
  if (!proto.close) {
    proto.close = function close(this: HTMLDialogElement) {
      this.removeAttribute('open');
      this.dispatchEvent(new Event('close'));
    };
  }
}

/* jsdom implements no scrolling: a surface that scrolls a log to its end would throw in the harness and
   work in a browser. The harness gains the method rather than the product losing the behaviour. */
if (!Element.prototype.scrollTo) {
  Element.prototype.scrollTo = function scrollTo(this: Element, options?: ScrollToOptions | number) {
    const top = typeof options === 'number' ? options : options?.top;
    if (typeof top === 'number') (this as HTMLElement).scrollTop = top;
  } as Element['scrollTo'];
}

/* jsdom does not implement matchMedia, and every motion or theme decision asks it first. */
if (!window.matchMedia) {
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
}

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  server.resetHandlers();
  window.location.hash = '';
});
afterAll(() => server.close());

/* jsdom implements no IntersectionObserver, and the workspace dashboard's sections use one to read only when
   they come near the screen. The harness observer never reports an intersection, which is what a section far
   below the fold sees: such a section does not read in a test unless its own control is used. */
if (typeof globalThis.IntersectionObserver === 'undefined') {
  class HarnessIntersectionObserver {
    readonly root = null;
    readonly rootMargin = '0px';
    readonly thresholds = [0];
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
    takeRecords(): IntersectionObserverEntry[] { return []; }
  }
  vi.stubGlobal('IntersectionObserver', HarnessIntersectionObserver);
}
