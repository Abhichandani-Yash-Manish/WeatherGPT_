"""Factual clauses are rendered from complete tool-owned tuples, never LLM prose."""
from datetime import datetime

def render_facts(result):
    lines=[];previous=None
    opening=result.get('lead')
    for fact in result['facts']:
        window=(fact.get('place',''),fact.get('start'),fact.get('end'),fact.get('year'),fact.get('period'))
        if window!=previous:
            heading='' if opening else fact.get('place','Source series')
            if heading and fact.get('start'):
                a=datetime.fromisoformat(fact['start']);b=datetime.fromisoformat(fact['end'])
                heading+=(f" · {a:%d %b %Y, %H:%M} IST (sample)" if fact.get('sample_at') else f" · {a:%d %b %Y, %H:%M}–{b:%d %b %Y, %H:%M} IST")
            elif heading and fact.get('year'):heading+=f" · {fact['period']} {fact['year']}"
            if heading:lines.append(heading)
            previous=window
        lines.append(f"{fact['label']}: {fact['value']} {fact['unit']} [{fact['id']}]")
    if any(f.get('start') and f.get('evidence_kind')!='reanalysis' for f in result['facts']):
        clause='These are model forecasts for the selected points, not observed conditions or district averages.'
        lines.append(clause)
        # Held beside the text: a written answer replacing this floor must still carry the semantics.
        result.setdefault('held_clauses',[]).append(clause)
    if result.get('status')=='partial':lines.append('Some requested information is missing; see the task results and limitations below.')
    return '\n'.join(lines)