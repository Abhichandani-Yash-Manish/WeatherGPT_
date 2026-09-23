"""Preserve a reader-selected point when the planner refers to that same place.

The home label is context, not a global override: another named place, an explicit
conflicting region or a non-point domain continues through its normal resolver.
"""
from .gazetteer import norm


def held_point(home, place, question):
    if not home or place.get('kind') not in {'settlement', 'unknown'}:
        return None
    name = norm(place.get('name') or '')
    label = str(home.get('label') or '')
    if not name or name not in {norm(home.get('name') or ''), norm(label.split(',')[0])}:
        return None
    # A planner can infer the famous city's state from its name. Only a region
    # explicitly named by the reader can overrule the already selected identity.
    for field in ('state', 'district'):
        region = norm(place.get(field) or '')
        if region and region not in norm(label) and region in norm(question):
            return None
    if not all(isinstance(home.get(k), (int, float)) for k in ('latitude', 'longitude')):
        return None
    return {
        'name': place['name'], 'for_place_name': place['name'], 'label': label,
        'coordinates': {k: home[k] for k in ('latitude', 'longitude')},
        'name_match_basis': 'the place selected by the reader, not a new name search',
        **({'admin1': home['state']} if home.get('state') else {}),
        **({'admin2': home['district']} if home.get('district') else {}),
    }
