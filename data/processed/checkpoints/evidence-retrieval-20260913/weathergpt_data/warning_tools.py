"""Report the warning source's evidence state without inventing an all-clear."""
from datetime import timedelta
from .foundation import Foundation
from .evidence_transport import evidence_store
from .transport import parsed,stamp,SourceError


def execute_warning(engine,result,plan,task):
    try:
        with evidence_store(engine.workspace,'imd_cap',engine.workspace.service.raw_root.parent/'warning-evidence') as store:
            foundation=Foundation.__new__(Foundation);foundation.store=store;packet=foundation.cap()
    except (ValueError,OSError) as exc:
        result.update(status='unavailable',answer='Current official warning evidence could not be verified: '+str(exc)+'. This is an evidence gap, not an all-clear.');return result
    records=packet['records'];assessment=packet['lifecycle_assessment'];meta=packet['provenance']
    latest=max(records,key=lambda m:parsed(m['sent'])) if records else None
    result['warning_evidence']={'assessment':assessment,'coverage':packet['coverage'],'delivery':meta['delivery'],'latest_sent':latest['sent'] if latest else None,'requested_places':plan['places'],'records':records}
    result['citations']=[{'id':'cap-feed','source_id':'S06','provider':'IMD-labelled CAP relay; origin authentication unverified','product':'Retrieved CAP feed state','url':meta['url'],'response_sha256':meta['sha256'],'retrieved_at_utc':meta['retrieved_at_utc']}]
    result['trace']['tools'].append({'name':'cap_lifecycle_assessment','retrieved_messages':len(records),'lifecycle_eligible':assessment['eligible_by_lifecycle'],'delivery':meta['delivery'],'official_applicability_verified':False})
    places=', '.join(p['name'] for p in plan['places']) or 'your location'
    summary=f"I cannot confirm current official warnings for {places}. The retrieved CAP relay contains {len(records)} messages; {assessment['eligible_by_lifecycle']} pass the time/status/reference checks."
    if latest:summary+=' Its newest message was sent '+latest['sent']+'.'
    summary+=' Geographic applicability, origin authentication and feed completeness are still unverified. This does not mean there are no warnings.'
    if meta['delivery']=='stale_cache':summary+=' The source refresh also failed; this is a cached feed assessment.'
    result.update(status='unavailable',answer=summary,expires_at_utc=stamp(engine.workspace.clock()+timedelta(minutes=5)))
    result['notes']+=['Warning source assessment only. Forecast rain, a bulletin warning table and CAP lifecycle eligibility do not establish a current applicable official warning.']
    return result
