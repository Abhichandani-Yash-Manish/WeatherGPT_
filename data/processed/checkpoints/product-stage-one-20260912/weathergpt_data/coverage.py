"""Immutable per-product coverage assessments; never infer no-warning from no-data."""
import json
import sqlite3
from pathlib import Path
from .geography import canonical, identity, required_text
from .transport import parsed


class Coverage:
    def __init__(self, database, readonly=False):
        path = Path(database).resolve()
        if readonly: self.db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            self.db = sqlite3.connect(path)
            self.db.execute('''CREATE TABLE IF NOT EXISTS coverage (
                coverage_id TEXT PRIMARY KEY, product TEXT NOT NULL, entity_id TEXT NOT NULL,
                variable TEXT NOT NULL, source_id TEXT NOT NULL, version TEXT NOT NULL,
                payload TEXT NOT NULL)''')
            self.db.execute('CREATE INDEX IF NOT EXISTS coverage_lookup ON coverage(product,entity_id,variable,source_id,version)')

    def close(self): self.db.close()

    def record(self, *, product, entity_id, variable, source_id, version, window_start, window_end,
               expected, fetched, validated, missing, quarantined, evidence, assessed_at,
               spatial='unresolved', temporal='unresolved', policy='reference_only',
               freshness_deadline=None, source_freshness='unknown', not_applicable_reason=None,
               notes=()):
        for k, v in [('product', product), ('entity_id', entity_id), ('variable', variable),
                     ('source_id', source_id), ('version', version)]: required_text(v, k)
        parsed(assessed_at)
        counts = [expected, fetched, validated, missing, quarantined]
        if any(type(x) is not int or x < 0 for x in counts): raise ValueError('Coverage counts must be nonnegative integers')
        if fetched > expected or validated + missing + quarantined != expected or validated + quarantined > fetched:
            raise ValueError('Coverage counts do not reconcile')
        if (window_start is None) != (window_end is None): raise ValueError('Both interval bounds required')
        if window_start is not None and parsed(window_end) <= parsed(window_start): raise ValueError('Coverage uses a nonempty half-open UTC interval')
        if temporal not in {'unresolved', 'validated'} or spatial not in {'unresolved', 'source_identity', 'validated'}:
            raise ValueError('Unknown applicability status')
        if policy not in {'reference_only', 'eligible', 'restricted', 'on_hold'}: raise ValueError('Unknown publication policy')
        if source_freshness not in {'unknown', 'validated', 'stale'}: raise ValueError('Unknown source freshness')
        if temporal == 'validated' and window_start is None: raise ValueError('Validated temporal applicability needs an interval')
        if freshness_deadline is not None and parsed(freshness_deadline) <= parsed(assessed_at):
            raise ValueError('Freshness deadline must follow assessment')
        if not evidence: raise ValueError('Coverage evidence required')
        if not_applicable_reason and any(counts): raise ValueError('Not-applicable requires zero expected records')
        if expected == 0 and not not_applicable_reason: raise ValueError('Zero expected is not proof of non-applicability')
        # Normalize equivalent timestamps so two offsets cannot create duplicate interval identities.
        from datetime import timezone
        if window_start is not None:
            window_start = parsed(window_start).astimezone(timezone.utc).isoformat()
            window_end = parsed(window_end).astimezone(timezone.utc).isoformat()
        key = [product, entity_id, variable, source_id, version, window_start, window_end]
        cid = identity(key)
        payload = dict(coverage_id=cid, product=product, entity_id=entity_id, variable=variable,
                       source_id=source_id, version=version, window_start=window_start, window_end=window_end,
                       expected=expected, fetched=fetched, validated=validated, missing=missing,
                       quarantined=quarantined, evidence=evidence, assessed_at=assessed_at,
                       spatial=spatial, temporal=temporal, policy=policy,
                       freshness_deadline=freshness_deadline, source_freshness=source_freshness,
                       not_applicable_reason=not_applicable_reason, notes=list(notes))
        old = self.db.execute('SELECT payload FROM coverage WHERE coverage_id=?', (cid,)).fetchone()
        if old and old[0] != canonical(payload): raise ValueError('Immutable assessment changed; use a new assessment version')
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO coverage VALUES (?,?,?,?,?,?,?)',
                            (cid, product, entity_id, variable, source_id, version, canonical(payload)))
        return cid

    def assess(self, coverage_id, now):
        moment = parsed(now)
        row = self.db.execute('SELECT payload FROM coverage WHERE coverage_id=?', (coverage_id,)).fetchone()
        if row is None: return {'status': 'unavailable', 'eligible': False, 'reasons': ['No recorded coverage assessment']}
        p = json.loads(row[0]); reasons = []
        if p['not_applicable_reason']:
            return {'status': 'not_applicable', 'eligible': False, 'reasons': [p['not_applicable_reason']], 'coverage': p}
        if p['validated'] != p['expected']: reasons.append('Incomplete validated values')
        if p['spatial'] != 'validated': reasons.append('Spatial applicability not validated')
        if p['temporal'] != 'validated': reasons.append('Temporal applicability not validated')
        if p['policy'] != 'eligible': reasons.append('Publication policy: ' + p['policy'])
        if p['source_freshness'] != 'validated': reasons.append('Publisher freshness: ' + p['source_freshness'])
        if p['freshness_deadline'] is None or moment >= parsed(p['freshness_deadline']):
            reasons.append('Assessment freshness deadline unknown or expired')
        if moment < parsed(p['assessed_at']): reasons.append('Assessment was not available at requested time')
        return {'status': 'blocked' if reasons else 'eligible', 'eligible': not reasons, 'reasons': reasons, 'coverage': p}
