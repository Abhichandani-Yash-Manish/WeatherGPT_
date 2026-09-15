import pathlib
p = pathlib.Path('docs/49-engine-architecture-and-gap-analysis.md')
t = p.read_text()
old = '## 1. What is measured today' + chr(10)
assert t.count(old) == 1
note = (old + chr(10) +
        'The table below is the pre-round audit of 15 September, taken before WS1 landed: it is the baseline' + chr(10) +
        'this plan was written against, and its numbers are deliberately not rewritten. The current' + chr(10) +
        'measurements live in the round sections below (the declared benchmark at 17/17 development cases and' + chr(10) +
        '4/4 holdout after round 5, the provider layer and the rules-first floor in round 1, the comparison,' + chr(10) +
        'alert, advisory, reading-position and briefcase batches in rounds 3-6). Nothing in this table is a' + chr(10) +
        'claim about today.' + chr(10))
t = t.replace(old, note, 1)
p.write_text(t)
print('noted')
