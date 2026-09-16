"""Forecast verification answers: archived runs measured against reanalysis, never a score.

Each figure is computed by the deterministic error-statistic contract over the hours both
the archived run and the ERA5 reference carry at the same valid time. The reference is a
modelled reanalysis, not a station observation; the upstream run identity is not exposed;
and the statistics describe one model, variable and window. They are not forecast skill, a
confidence, a risk or a ranking, and no single score is produced.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import re

from .adapters import PREVIOUS_RUNS, PREVIOUS_RUN_LEADS
from .answers import distance_km
from .geography import identity
from .transport import SourceError, parsed

IST = ZoneInfo('Asia/Kolkata')
MAX_DAYS = 31
DELAY_DAYS = 5
DEFAULT_WINDOW_DAYS = 14
# A day-level window inside the reanalysis delay cannot be measured. Week- and month-level
# periods without a parseable date fall back to the most recent completed window instead,
# which the answer names explicitly.
DAY_LEVEL = re.compile(r'\b(?:yesterday|last night|today|tonight|this (?:morning|afternoon|evening))\b', re.I)
LABELS = {'temperature_2m': 'Temperature (2 m)', 'precipitation': 'Precipitation'}
METRICS = {'bias': 'bias', 'mae': 'mean absolute error', 'rmse': 'root mean square error',
           'correlation': 'Pearson correlation'}
ALIASES = {'temperature': 'temperature_2m', 'temperature_2m': 'temperature_2m',
           'rain': 'precipitation', 'rainfall': 'precipitation', 'precipitation': 'precipitation'}


def requested_variables(parameters):
    mapped = list(dict.fromkeys(ALIASES.get(name, name) for name in (parameters or [])))
    supported = [name for name in mapped if name in PREVIOUS_RUNS]
    return supported or list(PREVIOUS_RUNS)


def model_for(quote):
    text = (quote or '').lower()
    return 'ecmwf_ifs025' if ('ecmwf' in text or 'ifs' in text) else 'gfs_seamless'


def _window(plan, now):
    """The completed UTC date window to verify, or a reason it cannot be verified yet."""
    today = now.astimezone(timezone.utc).date()
    if plan.get('start_local') and plan.get('end_local'):
        local_start = parsed(plan['start_local']).astimezone(IST)
        local_end = parsed(plan['end_local']).astimezone(IST)
        start = local_start.date()
        # A forecast window closes at 00:30 of the next local day; the verified date is the day before.
        end = local_end.date() - timedelta(days=1) if (local_end.hour, local_end.minute) == (0, 30) else local_end.date()
    else:
        end = today - timedelta(days=DELAY_DAYS + 1)
        start = end - timedelta(days=DEFAULT_WINDOW_DAYS - 1)
    latest = today - timedelta(days=DELAY_DAYS)
    if end > today:
        return None, None, ('Forecast verification needs a completed window; ' + end.isoformat() +
                            ' is not in the past.')
    if (today - end).days < DELAY_DAYS:
        return None, None, ('ERA5 hourly reanalysis is published with about a five-day delay, so a window '
                            'ending after ' + latest.isoformat() + ' cannot be verified yet.')
    if start > end or (end - start).days > MAX_DAYS - 1:
        raise SourceError('Forecast verification supports one to %d ordered completed days; '
                          'please narrow the window' % MAX_DAYS)
    return start, end, None


def render(result):
    facts = result.get('facts') or []
    if not facts:
        return 'No forecast verification could be computed. ' + ' '.join(result.get('notes', [])[:3])
    first = facts[0]
    lines = ['Forecast verification for ' + first['place'] + ' · ' + first.get('model', 'a model') +
             ' archived runs against ERA5 reanalysis, ' + first.get('window', '') + '.']
    for variable in ('temperature_2m', 'precipitation'):
        rows = [fact for fact in facts if fact['variable'] == variable and fact['metric'] == 'mae']
        if not rows:
            continue
        lines.append(LABELS.get(variable, variable) + ' mean absolute error by lead time: ' +
                     '; '.join('day ' + str(fact['lead_days']) + ' ' + str(fact['value']) + ' ' + fact['unit'] +
                               ' (' + str(fact['sample_hours']) + ' matched hours)' for fact in rows) + '.')
    lines.append('Every figure is computed over the hours the archived run and the reference both carry; '
                 'the tables below give the bias, mean absolute error, root mean square error and '
                 'correlation for each lead time. It is not forecast skill, a confidence or a risk, and '
                 'no model is ranked against another.')
    return '\n'.join(lines)


def execute_verification(engine, result, plan, task, resolved, coordinates):
    foundation = engine.workspace.foundation()
    now = engine.workspace.clock().astimezone(timezone.utc)
    variables = requested_variables(task.get('parameters'))
    model = model_for(task.get('request_quote'))
    explicit = bool(plan.get('start_local') and plan.get('end_local'))
    start, end, reason = _window(plan, now)
    if reason:
        result.update(status='unavailable', answer=reason, follow_up=None, verification=True)
        return result
    if not explicit and DAY_LEVEL.search(task.get('request_quote') or ''):
        latest = now.astimezone(timezone.utc).date() - timedelta(days=DELAY_DAYS)
        result.update(status='unavailable', follow_up=None, verification=True, answer=(
            'Forecast verification needs a completed window: the question names a single recent day, and '
            'ERA5 hourly reanalysis is published with about a five-day delay, so a window ending after ' +
            latest.isoformat() + ' cannot be measured yet. Name a completed window ending on or before that date.'))
        return result
    points = engine.resolve_points(result, plan, resolved, coordinates)
    if points is None:
        return result
    result.update(charts=[], calculations=[], verification=True)
    if not explicit:
        result['notes'].append('No past window was named, so the most recent completed fourteen-day window '
                               'was measured.')
    missing = []
    limits = []
    for place in points:
        try:
            data = foundation.verification(place['coordinates']['latitude'], place['coordinates']['longitude'],
                                           start.isoformat(), end.isoformat(), model=model,
                                           variables=variables, leads=list(PREVIOUS_RUN_LEADS))
        except (ValueError, OSError) as exc:
            missing.append(place['label'] + ': ' + str(exc)); continue
        citations = {}
        for role, packet in (('forecast', data['forecast']), ('reference', data['reference'])):
            citation = 'c-' + str(packet.get('sha256') or role)
            product = ('Archived ' + str(packet.get('model') or model) + ' runs at fixed lead-time offsets'
                       if role == 'forecast' else 'ERA5 hourly reanalysis, used as the reference')
            result['citations'].append({
                'id': citation, 'source_id': packet.get('source_id'), 'provider': 'Open-Meteo',
                'product': product, 'url': packet.get('url'), 'response_sha256': packet.get('sha256'),
                'retrieved_at_utc': packet.get('retrieved_at_utc'), 'requested_point': place['coordinates'],
                'returned_grid': packet.get('grid'),
                'grid_distance_km': round(distance_km(place['coordinates'], packet['grid']), 3)
                                   if packet.get('grid') else None,
                'model_run_time': None})
            citations[role] = citation
        result['trace']['tools'].append({'name': 'verification', 'model': model, 'variables': variables,
                                         'window': {'start': start.isoformat(), 'end': end.isoformat()},
                                         'source_sha256': data['forecast'].get('sha256')})
        window_label = start.isoformat() + ' to ' + end.isoformat()
        opened = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
        closed = datetime(end.year, end.month, end.day, tzinfo=timezone.utc) + timedelta(days=1)
        for variable in variables:
            for row in data['variables'].get(variable, []):
                lead = row['lead_days']
                if row.get('status') != 'measured':
                    missing.append('%s lead %d unmeasured: %d matched hours' % (variable, lead, row.get('n', 0)))
                    continue
                for metric in ('bias', 'mae', 'rmse', 'correlation'):
                    value = row.get(metric)
                    if value is None:
                        missing.append('%s lead %d %s undefined in this sample' % (variable, lead, metric))
                        continue
                    unit = data['units'].get(variable) if metric in ('bias', 'mae', 'rmse') else 'r'
                    result['facts'].append({
                        'id': 'f' + str(len(result['facts']) + 1),
                        'parameter': variable + '_' + metric,
                        'label': LABELS.get(variable, variable) + ' ' + METRICS[metric] + ' · lead ' +
                                 str(lead) + ' days',
                        'value': value, 'unit': unit, 'place': place['label'],
                        'entity_id': place.get('selection_id') or identity(place['coordinates']),
                        'start': opened.isoformat(), 'end': closed.isoformat(),
                        'source_id': data['forecast'].get('source_id'),
                        'evidence_kind': 'verification_statistic',
                        'evidence_version': data['forecast'].get('sha256'),
                        'citation_ids': [c for c in (citations.get('forecast'), citations.get('reference')) if c],
                        'method': data['method'].get(metric, metric) + ' over ' + str(row['n']) + ' matched hours',
                        'variable': variable, 'metric': metric, 'lead_days': lead,
                        'sample_hours': row['n'], 'model': model, 'window': window_label,
                        'computed': True})
        limits = list(data.get('limits') or [])
        result['notes'].append(model + ' archived runs matched to ERA5 hourly reanalysis over ' + window_label +
                               ' at the ' + str(data['forecast'].get('grid')) + ' grid cell.')
    result['notes'] += missing
    result['notes'] += limits
    result['notes'].append('The reference is ERA5 reanalysis, a modelled analysis rather than a station '
                           'observation; the upstream run identity is not exposed, and these statistics are '
                           'not forecast skill, a confidence, a risk or a model ranking.')
    result['status'] = 'answered' if result['facts'] and not missing else 'partial' if result['facts'] else 'unavailable'
    result['answer'] = render(result)
    return result
