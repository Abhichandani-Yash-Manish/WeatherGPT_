"""Historical comparison and descriptive series analysis from verified source rows."""
from decimal import Decimal,localcontext
from .research_answers import lookup_plan
from .tasks import expanded_years
from .transport import SourceError

def slope_per_decade(points):
    """OLS of annual values against actual years; no extrapolation or causal claim."""
    if len(points)<10:raise SourceError('A descriptive trend needs at least ten complete annual/seasonal samples')
    with localcontext() as context:
        context.prec=32
        n=Decimal(len(points));xs=[Decimal(x) for x,y in points];ys=[Decimal(y) for x,y in points]
        xbar=sum(xs)/n;ybar=sum(ys)/n
        denominator=sum((x-xbar)**2 for x in xs)
        if not denominator:raise SourceError('Trend needs distinct years')
        return str((10*sum((x-xbar)*(y-ybar) for x,y in zip(xs,ys))/denominator).quantize(Decimal('0.001')))

def execute_history(plan,task,lookup=lookup_plan):
    result={'status':'needs_clarification','answer':'','facts':[],'citations':[],'notes':[],'charts':[],'calculations':[],'lookups':[]}
    if task['operation']=='daily':
        result.update(status='unavailable',answer='This is a daily historical request. The daily reanalysis adapter is not connected to chat yet; an annual or monthly table cannot answer it.')
        return result
    if task['operation'] not in {'lookup','compare','series','trend'}:
        result.update(status='unavailable',answer='This historical operation is not implemented.');return result
    years=expanded_years(task);places=[plan['places'][i] for i in task['place_indices']]
    parameters=task['parameters']
    if not years and task.get('parameters')==['temperature']:
        # The stored district table carries rainfall; district temperature is not in it, and asking for a year
        # range would hide that. The national temperature table is separate and is named here.
        result.update(status='unavailable', answer='The stored district historical table carries rainfall, not district '
                       'temperature, so no year range is asked for a series that does not exist. National mean '
                       'temperature is published separately; ask for India temperature for a year to read that.')
        return result
    if not years:
        # A question that names no years is answered from the published range the source itself states, bounded
        # to the most recent thirty published years; the range is disclosed on the answer. Measured 18 September
        # 2026: six climate questions ("what is the average monsoon rainfall in Nashik district?") were answered
        # by asking for a year range although the stored series states its own coverage.
        from .research_answers import series_range
        spans={}
        for index in task['place_indices']:
            info=series_range({**plan,'places':[plan['places'][index]]})
            if info:spans[index]=info
        if not spans:
            result['answer']='Which year or year range should I look up?';return result
        last=max(info['last_year'] for info in spans.values())
        first=max(min(info['first_year'] for info in spans.values()),last-29)
        years=list(range(first,last+1))
        # The published series keeps its own historical spelling (Nasik for Nashik). The lookup is made under
        # the source's own name and the reading is disclosed, so a resolved series is actually read instead of
        # failing on the modern spelling while the range came from the old one.
        for index, info in spans.items():
            place=plan['places'][index]
            if str(info.get('district') or '').casefold()!=str(place.get('name') or '').casefold():
                result['notes'].append('Read as '+str(info['district'])+', '+str(info['state'])+
                    ' - the source district name ('+str(info.get('basis') or 'the publisher spelling')+').')
                place['name']=info['district']
                place['state']=info['state']
        result.setdefault('notes',[]).append('No year range was named, so the most recent published years '
            +str(first)+'-'+str(last)+' were read ('+', '.join(str(info['district'])+' '+str(info['first_year'])
            +'-'+str(info['last_year']) for info in spans.values())+'). The source states that coverage; it is not a choice of this workspace.')
    if not places:result['answer']='Which historical district and state, or All India, should I check?';return result
    if not parameters:result['answer']='Do you want historical rainfall, temperature, or both?';return result
    messages=[];complete=True;unsupported=[]
    for place in places:
        for parameter in parameters:
            if parameter not in {'rainfall','temperature'}:
                unsupported.append(parameter);complete=False;continue
            series=[];series_ids=[];unit=None;label=place['name'];group_facts=[]
            for year in years:
                query={**plan,'places':[place],'year':year,'period':task['period'],'history_parameter':parameter}
                try:value=lookup(query)
                except (ValueError,OSError) as exc:
                    # Integrity errors abort the task, never present them as source missingness.
                    if 'integrity' in str(exc).lower() or 'publication' in str(exc).lower():raise
                    value={'status':'unavailable','text':str(exc),'facts':[],'citations':[],'notes':[]}
                result['lookups'].append({'place':place,'parameter':parameter,'year':year,'evidence':value})
                result['notes']+=value.get('notes',[])
                if value.get('status')=='needs_selection' and value.get('choices'):
                    # The publisher's own series name differs from the asked name. Offer
                    # source-lined candidates and stop; nothing is substituted unasked.
                    result.update(status='needs_selection',answer=value['text'],choices=value['choices'],
                                  follow_up='Choose the source series, or give its exact district and state.')
                    return result
                if value['status']!='answered' or not value['facts']:
                    complete=False;messages.append(f"{place['name']}, {parameter}, {year}: {value['text']}")
                    series.append({'year':year,'value':None});continue
                f=dict(value['facts'][0]);f['id']='f'+str(len(result['facts'])+1)
                f['parameter']=parameter;f['entity_id']=(value.get('raw',{}).get('provenance',{}).get('series_id') or ('all-india' if place['kind']=='country' else f.get('place',place['name'])))
                f['citation_ids']=[]
                for citation in value['citations']:
                    c={**citation,'id':'c'+str(len(result['citations'])+1)};result['citations'].append(c);f['citation_ids'].append(c['id'])
                result['facts'].append(f);group_facts.append(f);series_ids.append(f['id']);unit=f['unit'];label=f['place']
                series.append({'year':year,'value':f['value'],'evidence_id':f['id']})
            if not group_facts:continue
            if len(years)>1:result['charts'].append({'kind':'historical_series','title':label+' · '+parameter+' · '+task['period'],'unit':unit,'points':series,'source_ids':sorted({f['source_id'] for f in group_facts}),'missing_values':'Explicit gaps, never interpolated'})
            if task['operation']=='compare':
                if len(years)!=2:
                    complete=False;messages.append('A numeric difference currently needs exactly two requested years. All available requested values are shown.')
                elif len(group_facts)==2:
                    a,b=group_facts;difference=Decimal(b['value'])-Decimal(a['value'])
                    result['calculations'].append({'operation':'difference','label':label+' · '+parameter,'value':str(difference),'unit':unit,'expression':f"{years[1]} minus {years[0]}",'input_ids':[a['id'],b['id']],'method':'Decimal subtraction of published values'})
                    messages.append(f"{label}: {parameter} changed by {difference} {unit} ({years[1]} minus {years[0]}).")
            if task['operation']=='trend':
                if len(group_facts)!=len(years):
                    complete=False;messages.append('Trend withheld because the requested series has missing values or unavailable years.')
                elif len(years)<10:
                    complete=False;messages.append('Trend withheld: provide at least ten years for this descriptive annual/seasonal/monthly series.')
                else:
                    value=slope_per_decade([(f['year'],f['value']) for f in group_facts])
                    result['calculations'].append({'operation':'linear_trend','label':label+' · '+parameter,'value':value,'unit':unit+'/decade','input_ids':series_ids,'sample_count':len(series_ids),'method':'OLS against actual calendar year; slope multiplied by 10; the record keeps 0.001 and the sentence states 0.1','interpretation':'Descriptive source-series slope, not homogenized climate change attribution or a future projection'})
                    # The source values are published to a tenth of a millimetre, so the sentence
                    # states one decimal and the calculation record keeps the full slope. Measured
                    # 17 September 2026: the answer read "54.654 mm/decade", more precision than the
                    # published values carry.
                    stated=format(Decimal(value).quantize(Decimal('0.1')),'f')
                    messages.append(f"{label}: descriptive {parameter} trend {stated} {unit}/decade over {min(years)}–{max(years)} ({len(years)} values), from a least-squares slope over the published values.")
    if unsupported:messages.append('Historical parameters not implemented: '+', '.join(unsupported)+'.')
    result['notes']=list(dict.fromkeys(result['notes']))
    if task['operation']=='trend':result['notes'].append('Source transcription is verified, but historical boundary comparability and homogeneity are unresolved. The descriptive slope is not proof of a statistically significant climate trend, causation or future conditions.')
    result['status']='answered' if complete else 'partial' if result['facts'] else 'unavailable'
    if not messages:messages.append(f"Retrieved {len(result['facts'])} published historical values for the requested places, parameters and years.")
    result['answer']='\n'.join(messages)
    return result
