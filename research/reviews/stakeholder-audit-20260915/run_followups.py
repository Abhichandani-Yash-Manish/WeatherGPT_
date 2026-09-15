"""Focused follow-up checks for observed gaps and missing-service behaviour."""
import base64, io, json, re, time, urllib.request, urllib.error, wave
from pathlib import Path
OUT=Path(__file__).resolve().parent
BASE='http://127.0.0.1:8765'
page=urllib.request.urlopen(BASE).read().decode()
token=re.search(r'name="workspace-token" content="([^"]+)"',page).group(1)
rows=[]
def call(label,path,body=None,authorized=True,base=BASE):
    headers={'Content-Type':'application/json'}
    if authorized:headers['X-WeatherGPT-Token']=token
    request=urllib.request.Request(base+path,json.dumps(body).encode() if body is not None else None,headers)
    started=time.monotonic()
    try:
        with urllib.request.urlopen(request,timeout=120) as response:
            status=response.status;packet=json.load(response)
    except urllib.error.HTTPError as error:
        status=error.code
        text=error.read().decode()
        try:packet=json.loads(text)
        except ValueError:packet={'error':text[:500]}
    except Exception as error:status=None;packet={'error':str(error)}
    rows.append({'id':label,'path':path,'request':body if 'speech' not in path else {'language':(body or {}).get('language'),'synthetic_audio':True},'http_status':status,'seconds':round(time.monotonic()-started,3),'packet':packet})
    (OUT/'followups.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    print(label,status,packet.get('status'),str(packet.get('error') or packet.get('answer') or '')[:180],flush=True)
    return packet
def ask(label,q,cid=None):return call(label,'/api/chat',{'question':q,**({'conversation_id':cid} if cid else {})})
original=json.load(open(OUT/'journeys.json'))
cid=next(r['packet']['conversation_id'] for r in original if r['id']=='forecast')
ask('context_measure_correct_thread','Instead, show temperature for that same place and time.',cid)
ask('history_rain_alone','Show India annual rainfall for 2024.')
ask('history_two_reversed','Show India annual mean temperature and rainfall for 2024.')
ask('warning_forecast','Will it rain in Patna tomorrow, and is there any warning?')
ask('water_level_control','What is the river water level at Patna tomorrow?')
ask('current_water_level_repeat','What is the observed water level near Patna, Bihar now?')
ask('hourly','Show hourly rainfall probability and temperature in Ahmedabad tomorrow morning.')
ask('strict_window','How much rain is forecast for Ahmedabad tomorrow from 09:15 to 12:15?')
ask('long_horizon','Will it rain in Ahmedabad 30 days from now?')
ask('daily_temperature','What was the ERA5-Land daily mean temperature in Ahmedabad from 5 through 7 August 2024?')
ask('notify_known_place','Notify me if there is a weather warning for Ahmedabad, Gujarat.')
ask('nonenglish_clarify','सुल्तानपुर में कल बारिश होगी?')
call('languages','/api/languages')
call('speech_missing_key','/api/speech/speak',{'text':'Test weather information.','language':'en'})
buffer=io.BytesIO()
with wave.open(buffer,'wb') as w:
    w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\0\0'*1600)
call('recognition_missing_key','/api/speech/transcribe',{'audio_base64':base64.b64encode(buffer.getvalue()).decode(),'language':'en','content_type':'audio/wav'})
call('speech_unverified_language','/api/speech/speak',{'text':'Test','language':'ta'})
call('api_requires_token','/api/conversations',authorized=False)
call('bad_request_rejected','/api/chat',{'question':'Weather','arbitrary_extra':True})
call('stored_conversations','/api/conversations')
call('actual_ollama_models','/api/tags',authorized=False,base='http://127.0.0.1:11434')
