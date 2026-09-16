"""Forecast verification: match archived lead-time runs to a reference and measure errors.

The reference is ERA5 reanalysis, which is a modelled analysis, not a station observation.
The statistics describe the matched sample for one model, variable, reference and window:
they are not operational skill, a confidence, a risk or a ranking of one model against
another. A pair is used only when both sides carry a value at the same valid hour; a lead
with too few matched hours is reported as unmeasured rather than given a number.
"""
from decimal import Decimal, localcontext

MIN_SAMPLE_HOURS = 24
METHOD = {
    'bias': 'mean of (forecast minus reference) over matched hours',
    'mae': 'mean of the absolute error over matched hours',
    'rmse': 'square root of the mean squared error over matched hours',
    'correlation': 'Pearson product-moment correlation over matched hours',
}


def _quantize(value):
    return value.quantize(Decimal('0.001'))


def error_statistics(pairs):
    """Deterministic error statistics over matched (forecast, reference) Decimal pairs."""
    n = len(pairs)
    if n < MIN_SAMPLE_HOURS:
        return {'n': n, 'status': 'unmeasured', 'reason': 'fewer than %d matched hours' % MIN_SAMPLE_HOURS}
    with localcontext() as context:
        context.prec = 32
        differences = [forecast - reference for forecast, reference in pairs]
        bias = sum(differences, Decimal(0)) / n
        mae = sum((abs(value) for value in differences), Decimal(0)) / n
        rmse = (sum((value * value for value in differences), Decimal(0)) / n).sqrt()
        forecasts = [forecast for forecast, _ in pairs]
        references = [reference for _, reference in pairs]
        forecast_mean = sum(forecasts, Decimal(0)) / n
        reference_mean = sum(references, Decimal(0)) / n
        covariance = sum(((forecast - forecast_mean) * (reference - reference_mean)
                          for forecast, reference in pairs), Decimal(0))
        forecast_variance = sum(((value - forecast_mean) ** 2 for value in forecasts), Decimal(0))
        reference_variance = sum(((value - reference_mean) ** 2 for value in references), Decimal(0))
        statistics = {'n': n, 'status': 'measured', 'bias': _quantize(bias),
                      'mae': _quantize(mae), 'rmse': _quantize(rmse)}
        if forecast_variance == 0 or reference_variance == 0:
            statistics['correlation'] = None
            statistics['correlation_note'] = 'undefined: one series has no variation in this sample'
        else:
            statistics['correlation'] = _quantize(covariance / (forecast_variance * reference_variance).sqrt())
        return statistics


def summarise(forecast, reference):
    """Match a previous-runs envelope to an ERA5 hourly envelope and measure per lead time."""
    reference_index = {}
    for record in reference.get('records') or []:
        if record.get('value') is None:
            continue
        reference_index[(record['variable'], record['valid_time_utc'])] = Decimal(str(record['value']))
    grouped = {}
    for record in forecast.get('records') or []:
        key = (record['variable'], record.get('lead_days'))
        bucket = grouped.setdefault(key, {'matched': [], 'hours': 0, 'missing': 0})
        bucket['hours'] += 1
        value = reference_index.get((record['variable'], record['valid_time_utc']))
        if value is None or record.get('value') is None:
            bucket['missing'] += 1
            continue
        bucket['matched'].append((Decimal(str(record['value'])), value))
    variables = {}
    for (variable, lead), bucket in grouped.items():
        statistics = error_statistics(bucket['matched'])
        statistics.update({'lead_days': lead, 'forecast_hours': bucket['hours'], 'unmatched_hours': bucket['missing']})
        variables.setdefault(variable, []).append(statistics)
    for rows in variables.values():
        rows.sort(key=lambda row: row['lead_days'])
    return {
        'schema_version': 'verification-result-v1',
        'method': METHOD,
        'minimum_sample_hours': MIN_SAMPLE_HOURS,
        'forecast': {'source_id': forecast.get('source_id'), 'model': forecast.get('coverage', {}).get('model'),
                     'grid': forecast.get('coverage', {}).get('returned_grid')},
        'reference': {'source_id': reference.get('source_id'), 'grid': reference.get('coverage', {}).get('returned_grid')},
        'variables': variables,
        'limits': [
            'The reference is ERA5 reanalysis, a modelled analysis, not a station observation.',
            'The statistics describe this sample for this model, variable and window; they are not operational skill, a confidence or a risk.',
            'A lead with fewer than %d matched hours is reported as unmeasured, not given a number.' % MIN_SAMPLE_HOURS,
            'A model is never ranked against another and no single skill score is produced.'],
    }
