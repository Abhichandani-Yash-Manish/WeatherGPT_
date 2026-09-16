/* An error boundary, so one broken surface states what broke instead of blanking the product.

   It renders the reader's own words about the failure: the error message is shown as the browser reported it,
   never prettified, and the two recoveries are named — go to Ask, or reload. Nothing is reported anywhere: the
   workspace keeps its questions and answers on this machine. */

import { Component, type ErrorInfo, type ReactNode } from 'react';

type Props = { children: ReactNode; onReset?: () => void };
type State = { error: Error | null };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    /* The console is for whoever is developing this machine, not a log the product ships. */
    if (typeof console !== 'undefined') console.error('WeatherGPT surface failed:', error, info.componentStack);
  }

  render(): ReactNode {
    const { error } = this.state;
    if (!error) return this.props.children;
    return (
      <section className="card mx-auto mt-8 max-w-2xl px-5 py-4" role="alert" data-testid="surface-error">
        <h1 className="display">This surface stopped</h1>
        <p className="reading mt-2">
          A component failed while rendering, so the surface was replaced by this notice rather than left blank.
          Nothing about your question was sent anywhere: the workspace answers on this machine only.
        </p>
        <p className="evidence mt-3 text-xs text-ink-soft">{String(error.message || error)}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              this.setState({ error: null });
              this.props.onReset?.();
            }}
          >
            Try this surface again
          </button>
          <button type="button" className="btn" onClick={() => window.location.reload()}>
            Reload the workspace
          </button>
        </div>
      </section>
    );
  }
}
