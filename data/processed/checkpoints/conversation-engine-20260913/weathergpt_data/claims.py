"""Factual clauses are rendered from complete tool-owned tuples, never LLM prose."""
from datetime import datetime

def render_facts(result):
    lines=[];previous=None
    for fact in result['facts']:
        window=(fact.get('place',''),fact.get('start'),fact.get('end'),fact.get('year'),fact.get('period'))
        if window!=previous:
            heading=fact.get('place','Source series')
            if fact.get('start'):
                a=datetime.fromisoformat(fact['start']);b=datetime.fromisoformat(fact['end'])
                heading+=(f" · {a:%d %b %Y, %H:%M} IST (sample)" if fact.get('sample_at') else f" · {a:%d %b %Y, %H:%M}–{b:%d %b %Y, %H:%M} IST")
            elif fact.get('year'):heading+=f" · {fact['period']} {fact['year']}"
            lines.append(heading);previous=window
        lines.append(f"{fact['label']}: {fact['value']} {fact['unit']} [{fact['id']}]")
    if any(f.get('start') and f.get('evidence_kind')!='reanalysis' for f in result['facts']):
        lines.append('These are model forecasts for the selected points, not observed conditions or district averages.')
    if result.get('status')=='partial':lines.append('Some requested information is missing; see the task results and limitations below.')
    return '\n'.join(lines)
