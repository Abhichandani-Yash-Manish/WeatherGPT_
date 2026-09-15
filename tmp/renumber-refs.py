import pathlib
fixes = {
    'docs/49-engine-architecture-and-gap-analysis.md': [('docs/61-chat-surface-and-provider-ux.md', 'docs/62-chat-surface-and-provider-ux.md')],
    'docs/31-full-solution-gap-register.md': [('61-chat-surface-and-provider-ux.md', '62-chat-surface-and-provider-ux.md')],
    'data/registry/hardening-progress.json': [('docs/61-chat-surface-and-provider-ux.md', 'docs/62-chat-surface-and-provider-ux.md')],
    'docs/62-chat-surface-and-provider-ux.md': [],
    'data/registry/product-progress.json': [('docs/61-chat-surface-and-provider-ux.md', 'docs/62-chat-surface-and-provider-ux.md')],
}
for path, pairs in fixes.items():
    p = pathlib.Path(path)
    t = p.read_text()
    for old, new in pairs:
        t = t.replace(old, new)
    p.write_text(t)
print('references renumbered')