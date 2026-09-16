import { render, screen } from '@testing-library/react';
import { ErrorBoundary } from './ErrorBoundary';

/* One broken component must not blank the product. The boundary states what failed, in the browser's own
   words, and offers two recoveries; nothing is reported anywhere, because nothing leaves this machine. */
function Broken(): JSX.Element {
  throw new Error('the surface could not read its payload');
}

describe('the error boundary', () => {
  it('states what failed and offers to try again', async () => {
    render(
      <ErrorBoundary>
        <Broken />
      </ErrorBoundary>,
    );
    const notice = screen.getByRole('alert');
    expect(notice).toHaveTextContent(/stopped/);
    expect(notice).toHaveTextContent('the surface could not read its payload');
    expect(screen.getByRole('button', { name: 'Try this surface again' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reload the workspace' })).toBeInTheDocument();
  });

  it('renders its children while nothing has failed', () => {
    render(
      <ErrorBoundary>
        <p>a working surface</p>
      </ErrorBoundary>,
    );
    expect(screen.getByText('a working surface')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
