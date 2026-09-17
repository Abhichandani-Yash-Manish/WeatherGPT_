import pathlib
path = pathlib.Path('frontend/src/modules/documentviewer.parity.test.tsx')
text = path.read_text()
extra = '''
  it('opens at the printed page a passage cited rather than at the first page', async () => {
    server.use(http.get('/api/documents/:sha', () => pdf()));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
    render(
      <QueryClientProvider client={client}>
        <DocumentViewer sha={SHA} title=\"Kamrup district bulletin\" page={3} onClose={() => {}} />
      </QueryClientProvider>,
    );
    const frame = await screen.findByTitle(/Saved source document/);
    expect(frame).toHaveAttribute('src', '/api/documents/' + SHA + '#page=3');
    /* The saved file itself is still the whole document: only the view opens at the cited page. */
    /* The same component with no page opens at the start. */
    render(
      <QueryClientProvider client={client}>
        <DocumentViewer sha={SHA} title=\"No page cited\" onClose={() => {}} />
      </QueryClientProvider>,
    );
    const plain = (await screen.findAllByTitle(/Saved source document/)).pop()!;
    expect(plain).toHaveAttribute('src', '/api/documents/' + SHA);
  });
'''
marker = "  it('trusts the row that says the body is held"
assert marker in text, 'marker not found'
text = text.replace(marker, extra + chr(10) + marker, 1)
path.write_text(text)
print('page-anchor check added')