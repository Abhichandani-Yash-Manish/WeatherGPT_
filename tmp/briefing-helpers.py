
def resolve_place(place, gazetteer=None):
    """A place name to a point, through the indexed gazetteer and its stated preference."""
    from .gazetteer import Gazetteer, preferred_match
    index = gazetteer or Gazetteer()
    name, _, state = str(place).partition(',')
    matches = index.search(name.strip(), state.strip())
    if not matches:
        raise SourceError('No indexed place matches: ' + str(place))
    chosen, why = preferred_match(matches)
    if chosen is None:
        raise SourceError('More than one place matches ' + str(place) + ' (' + str(why) +
                          '). Add the state or district to the place name.')
    admin1 = str(chosen.get('admin1') or '')
    return {'label': chosen.get('label') or chosen.get('name'), 'district': chosen.get('admin2') or chosen.get('name'),
            'state': admin1.removeprefix('State of ').strip(), 'latitude': chosen['coordinates']['latitude'],
            'longitude': chosen['coordinates']['longitude'], 'why': why}


def latest(directory):
    """The newest briefing record in a series directory, or None. Never guesses an order."""
    import pathlib
    folder = pathlib.Path(directory)
    if not folder.exists():
        return None
    records = sorted(folder.glob('record-*.json'))
    if not records:
        return None
    newest = records[-1]
    try:
        payload = json.loads(newest.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    markdown_path = newest.with_name(newest.name.replace('record-', 'briefing-')).with_suffix('.md')
    payload['markdown_path'] = str(markdown_path)
    payload['markdown'] = markdown_path.read_text(encoding='utf-8') if markdown_path.exists() else None
    payload['record_path'] = str(newest)
    return payload
