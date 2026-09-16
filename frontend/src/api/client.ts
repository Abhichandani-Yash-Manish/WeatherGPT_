/* One place that talks to the loopback workspace. The server checks a per-process session token on
   every request, answers with no-store, and refuses anything that is not loopback; this module carries
   the token from the page meta tag and turns an HTTP answer into a typed value or an ApiError that keeps
   the server's own wording. Nothing here invents a message: a failure says what the server said. */

export type ApiErrorKind = 'offline' | 'busy' | 'unavailable' | 'refused' | 'server';

export class ApiError extends Error {
  status: number;
  kind: ApiErrorKind;
  detail: string;
  /** The parsed JSON body when the server sent one: a route that answers 410 states what survives in fields,
      and a component must be able to read them rather than restate them. */
  body: Record<string, unknown> | null;

  constructor(message: string, status: number, kind: ApiErrorKind, detail = '', body: Record<string, unknown> | null = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.kind = kind;
    this.detail = detail;
    this.body = body;
  }
}

export function sessionToken(): string {
  const meta = document.querySelector('meta[name="workspace-token"]');
  return meta?.getAttribute('content') || '';
}

function classify(status: number, message: string): ApiErrorKind {
  if (status === 0) return 'offline';
  if (status === 429) return 'busy';
  if (/busy longer than the queue|maximum number of waiting/i.test(message)) return 'busy';
  if (status === 503 || status === 502 || status === 504) return 'unavailable';
  if (status >= 400 && status < 500) return 'refused';
  return status >= 500 ? 'unavailable' : 'refused';
}

/* The engine refuses a malformed request with a sentence a reader can act on ("Enter a question of 1-1500
   characters"). That sentence is the error message, so it is read out of the body rather than replaced. */
async function failure(response: Response): Promise<ApiError> {
  let message = 'The workspace answered HTTP ' + response.status + '.';
  let body: Record<string, unknown> | null = null;
  try {
    const text = await response.text();
    if (text) {
      try {
        const parsed = JSON.parse(text) as Record<string, unknown>;
        body = parsed;
        message = String(parsed.error || parsed.detail || message);
      } catch {
        message = text.slice(0, 400);
      }
    }
  } catch {
    /* the body could not be read: the status line stands as the message */
  }
  return new ApiError(message, response.status, classify(response.status, message), '', body);
}

export type RequestOptions = { signal?: AbortSignal; timeoutMs?: number };

export async function api<T>(path: string, init: RequestInit = {}, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(init.headers || {});
  headers.set('X-WeatherGPT-Token', sessionToken());
  // Only a JSON body gets a JSON content type: an audio upload keeps the boundary the browser set.
  if (typeof init.body === 'string' && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  /* A signal is created only when there is something to cancel or bound: a request that cannot be stopped
     and cannot time out should not carry a cancellation object at all. */
  const controller = options.signal || options.timeoutMs ? new AbortController() : null;
  const abort = () => controller?.abort();
  if (controller && options.signal) {
    if (options.signal.aborted) controller.abort();
    else options.signal.addEventListener('abort', abort);
  }
  const timer = controller && options.timeoutMs ? window.setTimeout(abort, options.timeoutMs) : 0;
  try {
    const response = await fetch(path, { ...init, headers, signal: controller ? controller.signal : undefined });
    if (!response.ok) throw await failure(response);
    if (response.status === 204) return undefined as T;
    const kind = response.headers.get('Content-Type') || '';
    if (kind.includes('json')) return (await response.json()) as T;
    return (await response.text()) as unknown as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if ((error as Error)?.name === 'AbortError') {
      throw new ApiError(
        'That request was stopped before the workspace answered it. The server may still be finishing it: nothing here' +
          ' claims it stopped, and the next read shows what it stored.',
        0,
        'offline',
        'aborted',
      );
    }
    throw new ApiError(
      'The workspace did not answer. It answers on this machine only: check that the server is still running.',
      0,
      'offline',
      String((error as Error)?.message || error),
    );
  } finally {
    if (timer) window.clearTimeout(timer);
    if (options.signal) options.signal.removeEventListener('abort', abort);
  }
}

export function getJson<T>(path: string, options?: RequestOptions): Promise<T> {
  return api<T>(path, { method: 'GET' }, options);
}

export function postJson<T>(path: string, body: unknown, options?: RequestOptions): Promise<T> {
  return api<T>(path, { method: 'POST', body: JSON.stringify(body ?? {}) }, options);
}

export function withQuery(path: string, params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    search.set(key, String(value));
  });
  const query = search.toString();
  return query ? path + '?' + query : path;
}
