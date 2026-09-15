import pathlib
p = pathlib.Path('weathergpt_data/workspace.py')
t = p.read_text()
old = "                results.append({'layer': name, 'place': target.get('label'), 'state': state,"
assert t.count(old) == 1, t.count(old)
new = ("                results.append({'layer': name, 'place': target.get('label'), 'state': state," + chr(10) +
       "                                'seconds': round(time.monotonic() - began, 1), 'detail': detail})" + chr(10) +
       "                self.warm_state['layers'] = list(results)  # progress a reader can watch, not a spinner")
t = t.replace(old, new, 1)
# the append inside the loop also wrote seconds/detail on the next line; remove the duplicate line
dup = "                                'seconds': round(time.monotonic() - began, 1), 'detail': detail})\n                self.warm_state['layers'] = list(results)  # progress a reader can watch, not a spinner\n                                'seconds': round(time.monotonic() - began, 1), 'detail': detail})"
if t.count(dup) == 1:
    t = t.replace(dup, "                                'seconds': round(time.monotonic() - began, 1), 'detail': detail})\n                self.warm_state['layers'] = list(results)  # progress a reader can watch, not a spinner", 1)
p.write_text(t)
print('warm progress recorded per layer')