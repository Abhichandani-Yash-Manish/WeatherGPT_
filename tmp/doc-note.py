import pathlib
path = pathlib.Path('docs/49-engine-architecture-and-gap-analysis.md')
text = path.read_text()
marker = '- Nothing here closes the alert journey (WS5) or the PS coverage matrix: it is one workstream step.'
addition = """

### The declared benchmark after the change

The same development and holdout sets were re-run after this work landed
(research/reviews/acceptance-benchmark-20260915j): **development 18/18 and holdout 4/4** again,
with no missing task, no shape mismatch, no prohibited claim and no abstained turn. The
compound-planning and comparison changes therefore did not regress the cases that round 2
closed. The holdout caveat from round 2 stands: it has been read before, so this is another
pass, not unseen-case proof."""
if 'declared benchmark after the change' not in text and marker in text:
    text = text.replace(marker, marker + addition, 1)
    path.write_text(text, encoding='utf-8')
    print('benchmark note added')
else:
    print('note not added:', 'declared benchmark after the change' in text, marker in text)
