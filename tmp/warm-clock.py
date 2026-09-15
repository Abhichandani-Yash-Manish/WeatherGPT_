import pathlib
p = pathlib.Path('weathergpt_data/workspace.py')
t = p.read_text()
old = "'finished_at_utc': stamp(self.clock())}"
assert t.count(old) == 1, t.count(old)
t = t.replace(old, "'finished_at_utc': self.clock().isoformat()}", 1)
old2 = "'detail': str(failure)[:200]}"
assert t.count(old2) == 1, t.count(old2)
t = t.replace(old2, "'detail': str(failure)[:200]}\n                self.warm_state['finished_at_utc'] = self.clock().isoformat()", 1)
p.write_text(t)
print('clock handling fixed')