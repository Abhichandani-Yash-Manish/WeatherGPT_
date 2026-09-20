"""A state is a state, not a village that happens to be spelled like one.

Measured 20 September 2026 against the scenario atlas. Asked "Are there any weather warnings in
Kerala today?", this product replied:

    Which place do you mean? Kerla, Pali District, State of Rājasthān / Kerāl, Jalore, State of
    Rājasthān / Rāmpura, Fazilka, State of Punjab / ...

Kerala is one of the thirty-six states and union territories of India. It was being handed to a
settlement search, which found four hamlets with similar names and offered them as candidates. The
same happened for Bihar, Punjab, Rajasthan, Gujarat and Uttarakhand - seven atlas failures with one
cause, and the most embarrassing thing this product could do in front of someone who named their
own state.

The state list is not invented here. It is read from the geography database, where the thirty-six
states and their districts are already stored as source-backed entities from the IMD agromet
directory (namespace S57), each carrying the evidence it came from.

ATTRIBUTION IS PARTIAL AND SAYS SO. The district warning product (S15) publishes no state for its
districts - only a label and a polygon - so a warning district is attributed to a state by matching
its name against the S57 directory. On the stored bulletin that matches 541 of 742 districts; the
rest are spelling differences the reviewed alias table does not cover (BELGAUM for Belagavi,
SHARANPUR for Saharanpur, MAYILADUTHURAI, which the directory does not list at all). Every count
this module produces therefore carries how many districts it could not attribute, because "27
districts in Gujarat" read as a complete count would be wrong, and a number whose incompleteness is
invisible is worse than no number.
"""
import json
import re
import sqlite3

# Names a reader may reasonably use for a state, mapped to the label the directory publishes. These
# are renames and official alternates, not transliteration guesses: each one is a name the state has
# actually been called in law or in common official use.
ALIASES = {
    'orissa': 'Odisha',
    'uttaranchal': 'Uttarakhand',
    'pondicherry': 'Puducherry',
    'delhi': 'New Delhi',
    'nct of delhi': 'New Delhi',
    'national capital territory of delhi': 'New Delhi',
    'j&k': 'Jammu and Kashmir',
    'jk': 'Jammu and Kashmir',
    'tamilnadu': 'Tamil Nadu',
    'westbengal': 'West Bengal',
    'andaman and nicobar islands': 'Andaman and Nicobar',
    'dadra and nagar haveli and daman and diu': 'Dadra And Nagar Haveli',
}


def norm(value):
    """Case, punctuation and spacing folded away; nothing else."""
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', str(value or '').lower()).split())


# Keyed the way a lookup will arrive: norm() folds punctuation away, so "J&K" becomes "j k" and an
# alias written with the ampersand would never be found by its own key.
ALIASES = {' '.join(re.sub(r'[^a-z0-9]+', ' ', key).split()): value for key, value in ALIASES.items()}


def _rows(database, kind, namespace=None):
    connection = sqlite3.connect(str(database))
    try:
        sql = "SELECT payload FROM entities WHERE kind=?"
        args = [kind]
        if namespace:
            sql += " AND namespace=?"
            args.append(namespace)
        for row in connection.execute(sql, args):
            try:
                yield json.loads(row[0])
            except ValueError:
                continue
    finally:
        connection.close()


class StateDirectory:
    """The thirty-six states and their districts, read from the geography database."""

    def __init__(self, database):
        self.database = database
        self._states = None
        self._districts = None

    def _load(self):
        if self._states is not None:
            return
        states = {}
        for payload in _rows(self.database, 'state'):
            label = payload.get('label')
            if label:
                states[norm(label)] = label
        districts = {}
        for payload in _rows(self.database, 'district', namespace='S57'):
            label = payload.get('label')
            state = (payload.get('attributes') or {}).get('source_state')
            if label and state:
                districts.setdefault(norm(label), (label, state))
        self._states, self._districts = states, districts

    def states(self):
        self._load()
        return sorted(self._states.values())

    def resolve(self, name):
        """The state a name denotes, or None. An alias is resolved, a settlement is not guessed."""
        self._load()
        key = norm(name)
        if not key:
            return None
        if key in self._states:
            return self._states[key]
        aliased = ALIASES.get(key)
        if aliased and norm(aliased) in self._states:
            return self._states[norm(aliased)]
        # "the state of Kerala", "Kerala state" - a reader may say either.
        stripped = norm(re.sub(r'^(the\s+)?state\s+of\s+|\s+state$', ' ', key))
        if stripped and stripped != key:
            return self.resolve(stripped)
        return None

    def state_of(self, district_label):
        """The state a district belongs to, or None when the directory does not list it."""
        self._load()
        found = self._districts.get(norm(district_label))
        return found[1] if found else None

    def districts_of(self, state_label):
        self._load()
        target = norm(state_label)
        return sorted(label for label, state in self._districts.values() if norm(state) == target)

    def attribute(self, records, state_label):
        """Split warning records into those attributed to this state and those attributed to none.

        Returns (matched, unattributed_count). The second number is not bookkeeping: it is how much
        of the bulletin this answer could not place, and it belongs in whatever the reader is told.
        """
        matched, unattributed = [], 0
        target = norm(state_label)
        for record in records:
            state = self.state_of(record.get('district_label'))
            if state is None:
                unattributed += 1
            elif norm(state) == target:
                matched.append(record)
        return matched, unattributed


def coverage_note(unattributed, total):
    """How much of the bulletin could not be placed in any state, in the reader's words."""
    if not unattributed:
        return ''
    return ('This count covers the districts that could be attributed to a state. ' +
            str(unattributed) + ' of the ' + str(total) + ' districts in the stored bulletin carry '
            'a name the reviewed district directory does not list - the warning product publishes no '
            'state of its own - so they are in neither this state nor any other, and a district of '
            'this state could be among them.')
