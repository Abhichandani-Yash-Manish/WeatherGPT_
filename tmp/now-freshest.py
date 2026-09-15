import pathlib
p = pathlib.Path('weathergpt_data/now_view.py')
t = p.read_text()
old = """    if stations:
        first = stations[0]
        age = first.get('age_minutes')
        lines.append('Nearest station ' + str(first.get('name') or first.get('station_code')) +
                     (' (' + str(round(float(first['distance_km']), 2)) + ' km)' if first.get('distance_km') is not None else '') +
                     ' reported at ' + str(first.get('observed_at_utc')) +
                     (', ' + str(age) + ' minutes before retrieval' if age is not None else '') + '.')
    else:"""
assert t.count(old) == 1, t.count(old)
new = """    if stations:
        first = stations[0]
        age = first.get('age_minutes')
        lines.append('Nearest station ' + str(first.get('name') or first.get('station_code')) +
                     (' (' + str(round(float(first['distance_km']), 2)) + ' km)' if first.get('distance_km') is not None else '') +
                     ' reported at ' + str(first.get('observed_at_utc')) +
                     (', ' + str(age) + ' minutes before retrieval' if age is not None else '') + '.')
        def minutes(station):
            value = station.get('age_minutes')
            return value if value is not None else 10 ** 9
        freshest = min(stations, key=minutes)
        if minutes(freshest) < minutes(first) and minutes(freshest) < 10 ** 9:
            lines.append('Freshest report in range: ' + str(freshest.get('name') or freshest.get('station_code')) +
                         ' at ' + str(freshest.get('observed_at_utc')) + ', ' + str(minutes(freshest)) +
                         ' minutes before retrieval. The nearest station is not always the freshest one.')
    else:"""
t = t.replace(old, new, 1)
p.write_text(t)
print('patched')