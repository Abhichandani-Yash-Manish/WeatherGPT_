import pathlib
p = pathlib.Path('weathergpt_data/product_api.py')
t = p.read_text()
view = ('''def now_view(foundation, latitude, longitude, refresh=False, now=None):
    """The right-now reading: observed, in force, and the next hours, kept apart."""
    from .now_view import NOT_CONNECTED, NOT_ESTABLISHED, compose
    reading = compose(foundation, latitude, longitude, now=now, refresh=refresh)
    limitations = list(reading.get('limitations') or [])
    limitations += [note for note in reading.get('not_connected') or [] if note not in limitations]
    return envelope('now.composed', 'ok' if reading.get('status') == 'ok' else 'unavailable', reading,
                    sources=[source_entry(source_id) for source_id in reading.get('sources') or []],
                    coverage={'stations': len((reading.get('observed') or {}).get('stations') or []),
                              'day': (reading.get('in_force') or {}).get('day'),
                              'hours': len((reading.get('next_hours') or {}).get('rows') or [])},
                    limitations=limitations, not_established=list(NOT_ESTABLISHED))


''')
anchor = "def registry_products():"
assert t.count(anchor) == 1, t.count(anchor)
t = t.replace(anchor, view + anchor, 1)
old_paths = "                 '/api/advisories/districts', '/api/personas')"
assert t.count(old_paths) == 1, t.count(old_paths)
t = t.replace(old_paths, "                 '/api/advisories/districts', '/api/personas', '/api/now')", 1)
old_dispatch = "    if path == '/api/personas':"
assert t.count(old_dispatch) == 1
t = t.replace(old_dispatch, "    if path == '/api/now':\n        latitude, longitude = _point_params(params)\n        return now_view(foundation, latitude, longitude, refresh=_flag(params, 'refresh'))\n    if path == '/api/personas':", 1)
p.write_text(t)
print('patched')