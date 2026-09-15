"""Resolve saved source fixtures from tracked curated evidence, not runtime caches.

The bulletin layout fixtures are real publisher PDFs whose bytes are recorded in
``research/implementation/*/verified-evidence`` (as ``<sha>.bin``) and
``research/implementation/*/source-pdfs`` (as ``<sha>.pdf``). Those trees are tracked by
Git, so a fresh checkout can run the layout tests without the ignored
``data/runtime`` cache. A blob already present under ``data/runtime/blobs`` is used
first when it exists, so a working tree that has re-ingested the corpus behaves exactly
as before. Missing material is a named failure rather than a silent skip.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_TRACKED = ('research/implementation/context-and-retrieval-20260913/verified-evidence',
            'research/implementation/evidence-retrieval-20260913/verified-evidence',
            'research/implementation/context-and-retrieval-20260913/source-pdfs')


def bulletin_path(sha):
    """The path of a saved source, or FileNotFoundError naming the fixture."""
    candidates = [ROOT / 'data' / 'runtime' / 'blobs' / (sha + '.bin')]
    for relative in _TRACKED:
        candidates.append(ROOT / relative / (sha + '.bin'))
        candidates.append(ROOT / relative / (sha + '.pdf'))
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        'Saved source fixture ' + sha + ' is not present in the working tree or the '
        'tracked curated evidence. Restore it from research/implementation or re-ingest '
        'the corpus; do not substitute a changed current bulletin.')


def bulletin_blob(sha):
    """The raw bytes of a saved source, or FileNotFoundError naming the fixture."""
    return bulletin_path(sha).read_bytes()
