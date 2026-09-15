"""Resolve immutable, already-tracked source fixtures without a runtime cache."""
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = [
    ROOT / 'research/implementation/evidence-retrieval-20260913/verified-evidence',
    ROOT / 'research/implementation/context-and-retrieval-20260913/source-pdfs',
]


def source_fixture(digest):
    for directory in DIRECTORIES:
        for suffix in ('.bin', '.pdf'):
            path = directory / (digest + suffix)
            if path.is_file():
                if sha256(path.read_bytes()).hexdigest() != digest:
                    raise AssertionError('Source fixture hash mismatch: ' + str(path))
                return path
    raise FileNotFoundError('Tracked source fixture missing: ' + digest)


# Compatibility for the stakeholder regression checks.
bulletin_path = source_fixture

def bulletin_blob(digest):
    return source_fixture(digest).read_bytes()
