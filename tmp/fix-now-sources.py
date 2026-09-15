import pathlib

nv = pathlib.Path('weathergpt_data/now_view.py')
t = nv.read_text()
anchor = "               'sources': [], 'not_connected': list(NOT_CONNECTED), 'not_established': list(NOT_ESTABLISHED),"
assert t.count(anchor) == 1, t.count(anchor)
t = t.replace(anchor, "               'sources': [], 'source_entries': [], 'not_connected': list(NOT_CONNECTED), 'not_established': list(NOT_ESTABLISHED),", 1)
old_collect = "        reading['limitations'] += [note for note in bundle.get('limitations') or [] if note not in reading['limitations']]"
assert t.count(old_collect) == 1
t = t.replace(old_collect, old_collect + "\n        reading['source_entries'] += [item for item in bundle.get('sources') or [] if isinstance(item, dict)]", 1)
old_warning = "        reading['limitations'] += [note for note in warning.get('limitations') or [] if note not in reading['limitations']]"
assert t.count(old_warning) == 1
t = t.replace(old_warning, old_warning + "\n        reading['source_entries'] += [item for item in warning.get('sources') or [] if isinstance(item, dict)]", 1)
old_forecast = "        reading['sources'] += [item for item in [hours_view.get('source_id')] if item]"
assert t.count(old_forecast) == 1
t = t.replace(old_forecast, old_forecast + "\n        reading['source_entries'] += [item for item in forecast.get('sources') or [] if isinstance(item, dict)]", 1)
nv.write_text(t)

pa = pathlib.Path('weathergpt_data/product_api.py')
pt = pa.read_text()
old = "                    sources=[source_entry(source_id) for source_id in reading.get('sources') or []],"
assert pt.count(old) == 1, pt.count(old)
new = ("                    sources=[source_entry(item.get('source_id'), item) for item in reading.get('source_entries') or []]\n"
       "                            or [source_entry(source_id, None) for source_id in reading.get('sources') or []],")
pt = pt.replace(old, new, 1)
pa.write_text(pt)
print('patched')