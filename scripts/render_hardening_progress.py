"""Render the living review checklist from its machine-readable record."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render():
    tracker = json.loads((ROOT/'data/registry/hardening-progress.json').read_text())
    review = (ROOT/tracker['review']).read_text()
    expected = set(re.findall(r'\| (R\d{2}) /', review))
    rows = tracker['findings']; ids = [r['id'] for r in rows]
    if set(ids) != expected or len(ids) != len(set(ids)):
        raise ValueError('Every review finding must appear exactly once')
    lines = ['# Living foundation checklist', '',
             'The [original review](../'+tracker['review']+') remains the historical analysis. '
             'This checklist records subsequent work; it does not rewrite earlier evidence.', '',
             '**Operational readiness: incomplete.** Nationwide and specialist SIH26068 scope remains unchanged.', '',
             'Machine source: [hardening-progress.json](../data/registry/hardening-progress.json). '
             'Regenerate with `python3 scripts/render_hardening_progress.py`; verify with `--check`.', '']
    for row in rows:
        lines += ['## '+row['id']+' — '+row['status'], '', row['current_evidence'], '',
                  '**Next:** '+row['next_action'], '', '**Closure evidence required:** '+row['acceptance'], '',
                  'Evidence: '+', '.join('['+Path(p).name+'](../'+p+')' for p in row['evidence'])+'.', '']
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--check',action='store_true')
    args = parser.parse_args(); text = render(); output = ROOT/'docs/08-hardening-progress.md'
    if args.check:
        if not output.exists() or output.read_text() != text: parser.exit(1,'Progress view is stale\n')
        print('PASS: all review findings present and progress view current')
    else: output.write_text(text)
