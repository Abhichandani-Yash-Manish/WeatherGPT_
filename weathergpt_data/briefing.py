"""Readable answer briefs over verified facts; wording never changes a fact's owner."""
from collections import defaultdict
from decimal import Decimal,InvalidOperation
from .transport import parsed

LABELS={
 'precipitation_probability':('Hourly rain chances','Har ghante barish ki sambhavna','हर घंटे बारिश की संभावना'),
 'precipitation':('Forecast precipitation','Barish ki anumaanit matra','अनुमानित वर्षा की मात्रा'),
 'temperature_2m':('Temperature','Taapmaan','तापमान'),
 'apparent_temperature':('Feels-like temperature','Mehsoos hone wala taapmaan','महसूस होने वाला तापमान'),
 'wind_speed_10m':('Wind speed','Hawa ki raftaar','हवा की गति'),
 'wind_gusts_10m':('Hourly maximum gust','Hawa ke jhonkon ki adhiktam raftaar','हवा के झोंकों की अधिकतम गति'),
 'visibility':('Visibility','Dikhai dene ki doori','दृश्यता'),
 'relative_humidity_2m':('Humidity','Nami','आर्द्रता'),
 'precipitation_sum':('Daily precipitation','Din bhar ki barish ki matra','दैनिक वर्षा की मात्रा'),
 'temperature_2m_mean':('Daily mean temperature','Din ka ausat taapmaan','दिन का औसत तापमान'),
 'temperature_2m_max':('Daily maximum temperature','Din ka adhiktam taapmaan','दिन का अधिकतम तापमान'),
 'temperature_2m_min':('Daily minimum temperature','Din ka nyuntam taapmaan','दिन का न्यूनतम तापमान'),
 'temperature_c':('Observed airport temperature','Airport par darj taapmaan','हवाई अड्डे पर दर्ज तापमान'),
 'wind_speed_kt':('Observed airport wind','Airport par darj hawa ki raftaar','हवाई अड्डे पर दर्ज हवा की गति')}


def short_place(value):
    # Display simplification only. The source entity and full label remain in every fact.
    return value.split(',')[0]


def render_brief(result):
    lang=result.get('plan',{}).get('language','en');locale=1 if lang=='hi-Latn' else 2 if lang=='hi' else 0
    facts=result.get('facts',[])
    # The opening sentence is owned by leadline and already states place, measure, value and window.
    # This renderer is the depth under it, so it drops its own receipt heading when one is present
    # rather than spelling the place and the window a second time.
    opening=result.get('lead')
    if not facts:
        if result.get('choices'):
            labels=list(dict.fromkeys(c['label'] for c in result['choices']))
            intro=['Which place do you mean?','Aap kis jagah ki baat kar rahe hain?','आप किस जगह की बात कर रहे हैं?'][locale]
            return intro+' '+ ' / '.join(labels[:4])+(['. Choose one, or type its state/district.','. Ek chuniye, ya uska rajya/zila likhiye.','। एक चुनें, या उसका राज्य/जिला लिखें।'][locale])
        if result['status']=='needs_clarification' and not result.get('plan',{}).get('places') and result.get('plan',{}).get('context_action')!='explain_previous' and any(t['kind'] in {'forecast','travel'} for t in result.get('plan',{}).get('tasks',[])):
            return ['Which city or village should I check?','Kis shehar ya gaon ke liye mausam bataun?','किस शहर या गाँव का मौसम बताऊँ?'][locale]
        return result['answer']
    if lang in {'hi','hi-Latn'} and all('year' in f and not f.get('start') for f in facts) and all(t['operation']=='lookup' for t in result['plan'].get('tasks',[])):
        lines=[]
        for f in facts:
            place=('पूरे भारत' if lang=='hi' else 'Poore Bharat') if f['place']=='All India' else f['place']
            parameter=f.get('parameter',f['label'])
            label=({'rainfall':'कुल वर्षा','temperature':'औसत तापमान'} if lang=='hi' else {'rainfall':'kul varsha','temperature':'ausat taapmaan'}).get(parameter,parameter)
            period=('वार्षिक' if lang=='hi' else 'saalana') if f['period']=='annual' else f['period']
            lines.append(f"{place} · {f['year']} ({period}): {label} {f['value']} {f['unit']}. [{f['id']}]")
        return '\n'.join(lines)
    # Keep published historical analyses and existing Gujarati templates intact.
    if lang=='gu' or not all(f.get('start') or f.get('observed_at') for f in facts):return result['answer']
    grouped=defaultdict(list)
    for fact in facts:grouped[(fact['place'],fact['source_id'])].append(fact)
    paragraphs=[];shown_calculations=set()
    for (place,source),group in grouped.items():
        p=short_place(place);first=group[0]
        observed=first.get('evidence_kind')=='observation'
        if observed:
            at=parsed(first['observed_at']).astimezone(__import__('zoneinfo').ZoneInfo('Asia/Kolkata')).strftime('%d %b, %H:%M')
            heading=[f'{p}, airport report at {at} IST:',f'{p}: {at} IST par airport ki report:',f'{p}: {at} IST की हवाई अड्डे की रिपोर्ट:'][locale]
        else:
            a=min(parsed(f['start']) for f in group);b=max(parsed(f['end']) for f in group)
            heading=f'{p} · {a:%d %b, %H:%M}–{b:%d %b, %H:%M} IST:'
        if opening:
            heading=heading if p != short_place(opening.split(':')[0]) else ''
        lines=[heading] if heading else [];params=defaultdict(list)
        for index,calc in enumerate(result.get('calculations',[])):
            if calc.get('kind')=='source_comparison' or set(calc.get('source_ids',[]))!={source} or not calc['label'].startswith(place+' · '):continue
            labels=['Total precipitation over this period','Is poore samay ki kul anumaanit barish','इस पूरी अवधि की कुल अनुमानित वर्षा']
            lines.append(labels[locale]+': '+calc['value']+' '+calc['unit']+'.');shown_calculations.add(index)
        for f in group:params[f['parameter']].append(f)
        for parameter,rows in params.items():
            label=LABELS.get(parameter,(rows[0]['label'],)*3)[locale]
            if parameter=='precipitation' and source=='S62' and len(rows)>1:label=['Precipitation in individual hours','Alag-alag ghanton mein barish ki matra','अलग-अलग घंटों में वर्षा की मात्रा'][locale]
            try:
                values=[Decimal(str(f['value'])) for f in rows]
                lo,hi=min(values),max(values);value=str(lo) if lo==hi else str(lo)+'–'+str(hi)
            except InvalidOperation:values=[];value=rows[0]['value']
            lines.append(f"{label}: {value} {rows[0]['unit']}.")
            if parameter=='precipitation_probability' and values:
                maximum=max(values);peak=rows[values.index(maximum)]
                a,b=parsed(peak['start']),parsed(peak['end'])
                lines.append([f'The highest hourly value is {maximum}% for {a:%d %b, %H:%M}–{b:%H:%M} IST.',f'Sabse zyada {maximum}% sambhavna {a:%d %b, %H:%M}–{b:%H:%M} IST ke ghante mein hai.',f'सबसे अधिक {maximum}% संभावना {a:%d %b, %H:%M}–{b:%H:%M} IST के घंटे में है।'][locale])
                clause=['These percentages are for individual hours, not the chance for the whole day.','Ye alag-alag ghanton ki sambhavnayein hain; poore din ka ek pratishat nahi.','ये अलग-अलग घंटों की संभावनाएँ हैं; पूरे दिन का एक प्रतिशत नहीं।'][locale]
                # Held beside the text: a written answer replacing this floor must still carry the semantics.
                lines.append(clause);result.setdefault('held_clauses',[]).append(clause)
        if source=='S22':
            clause=['ERA5 modeled history, not a rain-gauge observation.','Ye ERA5 ka aitihasik model-anumaan hai, rain-gauge ka maapa hua aankda nahi.','यह ERA5 का ऐतिहासिक मॉडल अनुमान है, वर्षामापी का प्रत्यक्ष आँकड़ा नहीं।'][locale]
            lines.append(clause);result.setdefault('held_clauses',[]).append(clause)
        elif observed:
            clause=['This report describes the airport, not conditions across the whole city.','Ye report airport ki hai, poore shehar ki nahi.','यह रिपोर्ट हवाई अड्डे की है, पूरे शहर की नहीं।'][locale]
            lines.append(clause);result.setdefault('held_clauses',[]).append(clause)
        elif source in {'S21','S62'}:
            model='GFS' if source=='S21' else 'Open-Meteo best-match'
            lines.append([f'Source: {model} forecast; conditions can change.',f'Srot: {model} ka poorvanuman; mausam badal sakta hai.',f'स्रोत: {model} पूर्वानुमान; मौसम बदल सकता है।'][locale])
        paragraphs.append(' '.join(lines))
    for index,calc in enumerate(result.get('calculations',[])):
        if index in shown_calculations or calc.get('kind')=='source_comparison':continue
        paragraphs.append(f"{calc['label']}: {calc['value']} {calc['unit']}.")
    if result.get('comparison_text'):paragraphs.append(result['comparison_text'])
    if result['status']=='partial':
        paragraphs.append(['Part of the request is still unresolved; the missing intervals or tasks are listed below.','Sawal ka kuch hissa abhi adhura hai; jo samay ya jaankari nahi mili, woh neeche di gayi hai.','सवाल का कुछ हिस्सा अभी अधूरा है; छूटे समय या जानकारी का विवरण नीचे है।'][locale])
    return '\n\n'.join(paragraphs)


def explain_evidence(result):
    if result.get('passages'):
        return 'Crop passages retain their source crop and stage labels. Separately labelled bulletin context includes general guidance and warning text from the same edition; it is not a verified current alert. Printed warning conditions are not extended by the bulletin forecast dates. Any incomplete context or opposing activity guidance remains unresolved. These sources do not establish your field conditions or grant a personal go/no-go decision.'
    language=result['plan'].get('language','en')
    parameters={f['parameter'] for f in result['facts']}
    texts=[]
    if any(f.get('evidence_kind')=='observation' for f in result['facts']):
        texts.append('METAR airport par us samay maape gaye mausam ki report hai. Taapmaan Celsius mein aur hawa ki raftaar knots mein hai. Ye aage ke mausam ka poorvanuman nahi hai.' if language=='hi-Latn' else 'A METAR is a snapshot of conditions measured at the airport at the stated time. Temperature is reported in Celsius and wind speed in knots. It is an observation, so it does not predict what happens later.')
    if 'precipitation_probability' in parameters:
        texts.append('Har pratishat apne dikhaye gaye ghante mein barish hone ki sambhavna hai. Isse barish ki matra nahi pata chalti; ghanton ke pratishat jodkar din ki sambhavna nahi nikal sakte.' if language=='hi-Latn' else 'Each percentage describes the chance of precipitation during its stated hour. It does not tell you the amount of rain; adding the hourly percentages cannot give a daily chance.')
    if 'precipitation' in parameters:
        texts.append('Millimetres barish ki matra batate hain, sambhavna nahi. Ye model ka anumaan hai, maapi hui barish nahi.' if language=='hi-Latn' else 'Millimetres describe precipitation amount, not the chance of rain. These are modeled amounts for the stated intervals, not measured rainfall.')
    if any(r['kind']=='taf' for r in result.get('airport_reports',[])):
        texts.append('A TAF is a forecast for the named airport over its stated validity period. The original report and change groups are preserved; they have not been turned into flight status or an operational clearance.')
    return ' '.join(texts) or 'The values apply only to their stated place, period and source. The existing source notes and missing information still apply.'