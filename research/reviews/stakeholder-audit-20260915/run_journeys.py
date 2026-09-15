"""Audit only: authored questions against the existing localhost app; no notifications."""
import json
import re
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

OUT = Path(__file__).resolve().parent
BASE = 'http://127.0.0.1:8765'
page = urllib.request.urlopen(BASE, timeout=10).read().decode()
token = re.search(r'name="workspace-token" content="([^"]+)"', page).group(1)
results = []

def ask(label, question, previous=None, language=None):
    body = {'question': question}
    if previous and previous.get('conversation_id'):
        body['conversation_id'] = previous['conversation_id']
    if language:
        body['output_language'] = language
    req = urllib.request.Request(BASE+'/api/chat', json.dumps(body).encode(),
                                 {'Content-Type':'application/json','X-WeatherGPT-Token':token})
    began = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=240) as response:
            status = response.status
            packet = json.load(response)
    except urllib.error.HTTPError as error:
        status = error.code
        packet = json.loads(error.read())
    except Exception as error:
        status, packet = None, {'error': type(error).__name__+': '+str(error)}
    row = {'id':label, 'question':question, 'checked_at_utc':datetime.now(timezone.utc).isoformat(),
           'http_status':status, 'seconds':round(time.monotonic()-began,3), 'packet':packet}
    results.append(row)
    (OUT/'journeys.json').write_text(json.dumps(results,indent=2,ensure_ascii=False)+'\n')
    print(label, status, packet.get('status'), row['seconds'],
          'facts',len(packet.get('facts') or []),'passages',len(packet.get('passages') or []),
          str(packet.get('error') or '')[:180],flush=True)
    return packet

forecast=ask('forecast','Will it rain in Ahmedabad, Gujarat tomorrow morning?')
afternoon=ask('followup_time','And what about the afternoon?',forecast)
ask('followup_measure','Instead, show temperature for that same place and time.',afternoon)
ask('gfs_comparison','Compare the models for rainfall in Ahmedabad tomorrow morning.')
ask('gfs_explicit','Use GFS for rainfall in Ahmedabad tomorrow morning.')
ask('wrf_explicit','Use WRF for rainfall in Ahmedabad tomorrow morning.')
ask('history_trend','Show the annual rainfall trend for Ahmedabad district, Gujarat from 1981 to 2010.')
ask('history_multi','Show India annual rainfall and mean temperature for 2024.')
ask('reanalysis','What was the daily mean relative humidity in Ahmedabad from 1 through 3 July 2024?')
ask('reanalysis_unsupported','ERA5-Land daily rainfall in Ahmedabad from 5 through 7 August 2024.')
ask('national_bulletin','What does the latest all India weather bulletin say about heavy rainfall?')
ask('crop_bulletin','What does the Ahmedabad district agromet advisory say for cotton?')
ask('crop_decision','Can I irrigate cotton in Ahmedabad, Gujarat this week?')
ask('hindi','कल अहमदाबाद, गुजरात में सुबह बारिश होगी?')
ask('gujarati','અમદાવાદમાં આવતીકાલે સવારે વરસાદ થશે?')
ask('tamil_output','Will it rain in Ahmedabad tomorrow morning?',language='ta')
ask('ambiguity','Will it rain in Sultanpur tomorrow?')
ask('typo','Will it rain in Ahmedbad, Gujrat tomorrow?')
ask('warning','Is any warning in force for Patna, Bihar today?')
ask('now','What is it like right now in Ahmedabad?')
ask('airport','What is the current weather at VOBL?')
ask('marine','What are the wave conditions off Kochi tomorrow?')
ask('river','What is the river discharge near Patna, Bihar tomorrow?')
ask('water_level','What is the observed water level near Patna, Bihar now?')
ask('tide','What is the tide at Kochi tomorrow?')
ask('notification','Notify me if a cyclone warning is issued for Kochi.')
ask('novel_llm','My clothes are drying outside in Ahmedabad; which hours tomorrow would be better for bringing them inside?')
