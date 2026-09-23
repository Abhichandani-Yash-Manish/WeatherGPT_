from weathergpt_data.held_point import held_point

HOME = {'label': 'Jaipur, Yamunanagar, State of Haryāna', 'name': 'Jaipur',
        'latitude': 30.05564, 'longitude': 77.21282}

def place(name='Jaipur', state='', kind='settlement', district=''):
    return dict(name=name, state=state, kind=kind, district=district)

def test_selected_village_is_not_replaced_by_the_famous_namesake():
    result = held_point(HOME, place(state='Rajasthan'), 'Will it rain in my selected place tomorrow?')
    assert result['label'] == HOME['label']
    assert result['coordinates'] == {'latitude': 30.05564, 'longitude': 77.21282}
    assert 'not a new name search' in result['name_match_basis']

def test_a_different_named_place_is_still_resolved_normally():
    assert held_point(HOME, place(name='Mumbai'), 'What about Mumbai?') is None

def test_an_explicit_conflicting_state_wins_over_home():
    assert held_point(HOME, place(state='Rajasthan'), 'What about Jaipur, Rajasthan?') is None

def test_an_explicit_conflicting_district_wins_over_home():
    assert held_point(HOME, place(district='Dibrugarh'), 'Rain in Jaipur, Dibrugarh?') is None

def test_non_point_domains_and_missing_home_are_not_substituted():
    for kind in ['district','state','country','sea_area','relative']:
        assert held_point(HOME, place(kind=kind), 'weather here') is None
    assert held_point(None, place(), 'weather here') is None

def test_missing_coordinates_do_not_invent_a_point():
    assert held_point({'label':'Jaipur'}, place(), 'weather here') is None

def test_resolver_replaces_an_old_same_name_resolution_with_the_current_selection():
    from types import SimpleNamespace
    from weathergpt_data.conversation import ConversationEngine
    engine = ConversationEngine.__new__(ConversationEngine)
    engine._local = SimpleNamespace(reader_home=HOME, reader_place=None)
    engine._stage = lambda _: None
    # Searching is forbidden in this case: the reader selected a complete point.
    engine.gazetteer = SimpleNamespace(search=lambda *args: (_ for _ in ()).throw(AssertionError('re-searched selected place')))
    old = {'Jaipur': {'label': 'Jaipur, Rajasthan', 'coordinates': {'latitude': 26.9, 'longitude': 75.8}}}
    packet = {'question': 'Will it rain in my selected place tomorrow?', 'notes': [], 'trace': {'tools': []}}
    points = engine.resolve_points(packet, {'places': [place(state='Rajasthan')]}, old, None)
    assert points[0]['label'] == HOME['label']
    assert packet['resolved_points']['Jaipur']['coordinates']['latitude'] == HOME['latitude']
    assert packet['trace']['tools'][0]['name'] == 'reader_selected_point'
