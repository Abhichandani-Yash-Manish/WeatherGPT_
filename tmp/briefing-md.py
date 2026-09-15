
def summary_line(briefing):
    """One line a runner can print: what the run read, and what it did not."""
    day_states = [_day_state(record)['state'] for record in briefing.get('places') or []]
    quiet = day_states.count('quiet')
    not_read = day_states.count('not_read')
    return ('%d place(s) · official day read for %d · quiet in the product for %d · not read for %d · change: %s'
            % (briefing.get('place_count') or 0, len(day_states) - not_read, quiet, not_read,
               (briefing.get('change_since_previous') or {}).get('reading')))


def load_previous(path):
    """The previous run in this series, read from its own record, or None."""
    if not path or not path.exists():
        return None
    try:
        record = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return record.get('briefing') if isinstance(record, dict) and 'briefing' in record else record


def markdown(briefing):
    """The briefing as Markdown: what each product said, and what it did not say."""
    lines = ['# Briefing — ' + str(briefing.get('generated_at_utc')), '',
             '- Briefing identity: sha256 ' + str(briefing.get('briefing_id'))[:16] + ' (the content hash of this briefing)',
             '- Places: ' + str(briefing.get('place_count')) + ' · Official day: day ' + str(briefing.get('day_number')) +
             ' of the published product · Forecast days: ' + str(briefing.get('forecast_days')),
             '- Sources named: ' + (', '.join(briefing.get('sources') or []) or 'none'),
             '- This is a reading of published products for named places. It is not a warning, not an all-clear, not advice and not delivered.',
             '']
    for record in briefing.get('places') or []:
        lines.append('## ' + str(record.get('label')))
        lines.append('')
        where = str(record.get('district') or 'no district matched')
        if record.get('state'):
            where += ', ' + str(record['state'])
        lines.append('- Place: ' + where + ' (' + str(record.get('latitude')) + ', ' + str(record.get('longitude')) + ')')
        day = record.get('official_day')
        if day:
            lines.append('- Official district warning day: ' + str(day.get('status_line')) +
                         ' · colour code ' + str(day.get('colour_code')) + ' · source ' + str(day.get('source_id')) +
                         ' · issued ' + str(day.get('issued_at_utc')) + ' · retrieved ' + str(day.get('retrieved_at_utc')))
            lines.append('- Day window: ' + str(day.get('day_label')) + ' (' + str(day.get('starts_utc')) + ' to ' + str(day.get('ends_utc')) + ')')
            if day.get('official_wording'):
                lines.append('- Printed wording: "' + str(day['official_wording']) + '"')
            elif day.get('quiet'):
                lines.append('- Printed wording: the product states a colour and hazard codes for this district-day and no free-text wording is recorded.')
        relay = record.get('relay')
        if relay:
            lines.append('- CAP relay (a separate product, never merged with the day above): ' +
                         ('not read' if relay.get('messages') is None else str(relay.get('messages')) + ' message(s), ' +
                          str(relay.get('eligible_by_lifecycle')) + ' eligible by lifecycle') + '. ' + str(relay.get('note') or ''))
        forecast = record.get('forecast')
        if forecast and forecast.get('window'):
            lines.append('- Forecast window (model output for a grid cell, not an observation; first and last value of the retrieved series):')
            for name, entry in forecast['window'].items():
                lines.append('    - ' + name + ': ' + str(entry.get('first')) + ' → ' + str(entry.get('last')) +
                             (' ' + str(entry['unit']) if entry.get('unit') else '') + ' across ' + str(entry.get('samples')) +
                             ' sample(s) · ' + str(entry.get('model') or 'model not stated'))
        for item in record.get('unavailable') or []:
            lines.append('- Not read: ' + str(item.get('part')) + ' — ' + str(item.get('why')))
        lines.append('')
    change = briefing.get('change_since_previous') or {}
    lines += ['## Change since the previous run', '', '- Reading: ' + str(change.get('reading')) + ' · ' + str(change.get('detail')), '']
    if change.get('previous_generated_at_utc'):
        lines.append('- Compared with the run of ' + str(change['previous_generated_at_utc']) + ' (sha256 ' +
                     str(change.get('previous_briefing_id'))[:16] + ')')
    for item in change.get('day_changes') or []:
        if item.get('reading') == 'changed':
            lines.append('- ' + str(item['place']) + ': ' + str((item.get('from') or {}).get('summary')) + ' → ' +
                         str((item.get('to') or {}).get('summary')))
        elif item.get('reading') == 'not_comparable':
            lines.append('- ' + str(item['place']) + ': not comparable between these two runs — ' + str(item.get('detail')))
    if change.get('places_added'):
        lines.append('- Places added: ' + ', '.join(change['places_added']))
    if change.get('places_removed'):
        lines.append('- Places removed: ' + ', '.join(change['places_removed']))
    lines += ['', '## What is not established here', '']
    lines += ['- ' + item for item in briefing.get('not_established') or []]
    return chr(10).join(lines) + chr(10)
