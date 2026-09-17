"""Loopback-only forecast workspace. Database reads and explicit bounded refreshes."""
import argparse
import hmac
import json
import re
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .answers import AnswerService, ROOT
from .ingestion import IngestionDB, run_one
from .rag import context_from_answer
from .documents import DocumentPruned
from .ratelimit import RateLimited
from .speech import LanguageServiceUnavailable
from .transport import SourceError, parsed, utcnow

DEFAULT_DATABASE=ROOT/'data/runtime/ingestion/ingestion.sqlite'
DEFAULT_RAW=ROOT/'data/runtime/ingestion/raw'
DEFAULT_GEOGRAPHY=ROOT/'data/processed/geography/source-inventory-20260912-v1/geography.sqlite'
# Document bodies are pruned after this many days; extracted passages and hashes are kept.
RETENTION_DAYS=7



class Workspace:
    def __init__(self, database=DEFAULT_DATABASE, raw_root=DEFAULT_RAW, geography=DEFAULT_GEOGRAPHY, clock=utcnow, opener=None,
                 frontend='react'):
        # Which frontend this process serves: 'react' (web/dist, built by frontend/) is the only surface since
        # R6 removed the vanilla tree, and the command line refuses 'legacy' in words rather than serving a
        # 404 page for it. Both values speak the same API and the same token contract.
        self.frontend=frontend
        self.service=AnswerService(database,raw_root,geography,clock=clock)
        self.clock=clock;self.opener=opener
        self.conversation=None
        self._conversation_lock=threading.Lock()
        self._foundation=None

    def chat(self,body):
        return self.engine().ask(body)

    def chat_preview(self,body):
        """The first reading of a question, while the real turn is still working. Never evidence.

        It shares the conversation engine so it reads the same conversation state the answer will,
        and it takes no place in the wait queue: it plans with the deterministic rules only and
        acquires nothing.
        """
        return self.engine().preview(body)

    def engine(self):
        from .conversation import ConversationEngine
        if self.conversation is None:
            with self._conversation_lock:
                if self.conversation is None:self.conversation=ConversationEngine(self)
        return self.conversation

    def watch_store(self):
        from .watches import WatchStore
        return WatchStore(self.service.ingestion_database.parent/'watches.sqlite')

    def briefcase_store(self):
        from .briefcase import BriefStore
        return BriefStore(self.service.ingestion_database.parent/'briefcase.sqlite')

    def briefs(self):
        """The local briefcase: briefs the workspace composed, kept, and never delivered."""
        from .briefcase import NO_DELIVERY
        entries=[]
        for entry in self.briefcase_store().list():
            entries.append({'id':entry['id'],'saved_at':entry['saved_at'],'kind':entry['kind'],'title':entry['title'],
                            'place':entry['place'],'window':entry['window'],'content_sha256':entry['content_sha256'],
                            'sources':entry['sources'],'status':entry['payload'].get('status'),'evidence':entry['evidence'],
                            'delivery':entry['delivery']})
        return {'schema_version':'briefcase-v1','delivery':'local_only_no_delivery','note':NO_DELIVERY,'briefs':entries}

    def saved_brief(self,brief_id):
        """One kept brief with the Markdown it exports to."""
        from .briefcase import markdown
        entry=self.briefcase_store().get(brief_id)
        return {'schema_version':'briefcase-entry-v1','delivery':'local_only_no_delivery','entry':entry,
                'markdown':markdown(entry)}

    def brief_export(self,brief_id):
        """The export pair: a file name derived from the entry, and the Markdown itself."""
        from .briefcase import markdown
        entry=self.briefcase_store().get(brief_id)
        safe=re.sub(r'[^a-z0-9]+','-',str(entry['title']).lower()).strip('-')[:60] or 'brief'
        return safe+'-'+str(entry['id'])[:8]+'.md',markdown(entry)

    def briefings_dir(self):
        return self.service.ingestion_database.parent.parent/'briefings'

    def latest_briefing(self):
        """The newest briefing in this workspace's series directory, or how to write one."""
        from .briefing_run import RUNNER_NOTE, latest
        import json
        directory=self.briefings_dir()
        view={'schema_version':'briefing-latest-v1','present':False,'directory':str(directory),'note':RUNNER_NOTE,
              'detail':('Nothing is delivered, pushed or scheduled by the workspace itself. No briefing has been written to '
                        'this series directory yet: write one with python3 scripts/briefing.py --place "<place>" '
                        '--out ' + str(directory) + '.'),
              'run':None,'briefing':None,'markdown':None,'series':[]}
        found=latest(directory)
        if not found:return view
        runs=[]
        index=directory/'index.json'
        if index.exists():
            try:
                rows=json.loads(index.read_text(encoding='utf-8')).get('runs') or []
                runs=[{'run':row.get('run'),'generated_at_utc':row.get('generated_at_utc'),'briefing_id':row.get('briefing_id'),
                       'change':row.get('change'),'latency_seconds':row.get('latency_seconds'),'interval_seconds':row.get('interval_seconds'),
                       'place_count':row.get('place_count')} for row in rows][-12:]
            except (OSError,ValueError,TypeError):runs=[]
        record=found or {}
        briefing=record.get('briefing') or {}
        view.update(present=True,run={'generated_at_utc':briefing.get('generated_at_utc'),'briefing_id':briefing.get('briefing_id'),
                                      'place_count':briefing.get('place_count'),'day_number':briefing.get('day_number'),
                                      'forecast_days':briefing.get('forecast_days'),'sources':briefing.get('sources') or [],
                                      'change':(briefing.get('change_since_previous') or {}).get('reading'),
                                      'latency_seconds':record.get('latency_seconds'),'interval_seconds':record.get('interval_seconds'),
                                      'record_path':record.get('record_path'),'markdown_path':record.get('markdown_path'),
                                      'runner_note':record.get('runner_note') or RUNNER_NOTE},
                    briefing=briefing,markdown=record.get('markdown'),series=runs)
        return view


    def warm(self, body):
        """Read the slow layers for one point now, so the first ask is not the wait."""
        if not isinstance(body, dict):
            raise SourceError('Send the warm request as JSON')
        latitude, longitude = body.get('lat'), body.get('lon')
        if latitude is None or longitude is None:
            raise SourceError('Warming reads the layers for one point: give lat and lon')
        state = self.start_warming([{'latitude': float(latitude), 'longitude': float(longitude),
                                      'label': str(body.get('label') or 'the working place')}])
        return {'schema_version': 'warm-v1', 'state': state.get('state'),
                'note': ('The slow connected layers are being read for this place in the background. Nothing is inferred '
                         'from a warm-up; a failure is recorded and the ask retrieves as it always did.')}
    def run_briefing(self, body):
        """Compose a briefing for the working place and write it into this workspace's series.

        The page action and the command line produce the same artefact: the Markdown, the full
        record and the series index row. Nothing is delivered, pushed or scheduled by this - a
        run happens when someone asks for one, in the foreground.
        """
        from .briefing_run import compose, load_previous, resolve_place, series_entry, update_index, write_run
        import time
        if not isinstance(body, dict):
            raise SourceError('Send the briefing request as JSON')
        latitude, longitude = body.get('lat'), body.get('lon')
        label = str(body.get('label') or '').strip()
        place = None
        if body.get('place'):
            place = resolve_place(str(body['place']))
            latitude, longitude = place['latitude'], place['longitude']
            label = label or place.get('label')
        if latitude is None or longitude is None:
            raise SourceError('A briefing is composed for a point: give lat and lon, or a place name')
        hours = int(body.get('hours') or 6)
        if hours not in (6, 12, 24):
            raise SourceError('Ask for 6, 12 or 24 model hours')
        place = place or {'label': label or 'the requested point', 'latitude': float(latitude), 'longitude': float(longitude)}
        directory = self.briefings_dir()
        records = sorted(directory.glob('record-*.json')) if directory.exists() else []
        previous = load_previous(records[-1]) if records else None
        began = time.monotonic()
        briefing = compose(self.foundation(), [place], day=int(body.get('day') or 1),
                           forecast_days=int(body.get('forecast_days') or 3), now=self.clock(), previous=previous)
        latency = round(time.monotonic() - began, 3)
        runs = 0
        index_path = directory / 'index.json'
        if index_path.exists():
            try:
                runs = len(json.loads(index_path.read_text(encoding='utf-8')).get('runs') or [])
            except (OSError, ValueError):
                runs = 0
        markdown_path, record_path, _stamp = write_run(directory, briefing, latency,
                                                       runner='the workspace briefing action')
        update_index(directory, series_entry(briefing, markdown_path, record_path, latency, run_number=runs + 1))
        return {'schema_version': 'briefing-run-v1', 'delivery': 'local_only_no_delivery',
                'note': ('A briefing records what the connected products published at the instant it ran. Nothing was delivered, '
                         'pushed or scheduled; a run happens when someone asks for one.'),
                'entry': {'run': runs + 1, 'generated_at_utc': briefing['generated_at_utc'],
                          'briefing_id': briefing['briefing_id'], 'place_count': briefing['place_count'],
                          'latency_seconds': latency, 'change': (briefing.get('change_since_previous') or {}).get('reading'),
                          'markdown_path': str(markdown_path), 'record_path': str(record_path)},
                'briefing': briefing, 'markdown': markdown_path.read_text(encoding='utf-8')}
    def save_brief(self,body):
        """Compose a brief from sources and keep it. The client asks for a brief; it cannot post one."""
        if not isinstance(body,dict):raise SourceError('Send the brief request as JSON')
        kind=body.get('kind')
        if kind not in ('alert_brief','advisory_brief'):raise SourceError('Save an alert brief or an advisory brief')
        if kind=='alert_brief':
            from . import product_api
            latitude,longitude=body.get('lat'),body.get('lon')
            if latitude is None or longitude is None:
                raise SourceError('An alert brief is composed for a point: give lat and lon')
            day=body.get('day')
            view=product_api.alert_brief_view(self.foundation(),float(latitude),float(longitude),
                                              day=int(day) if day is not None else None)
            brief=view.get('data') or {}
        else:
            brief=self.advisory_brief(body)
        entry=self.briefcase_store().save(kind,brief,now=self.clock())
        return {'schema_version':'briefcase-entry-v1','delivery':'local_only_no_delivery','entry':entry,
                'saved':True,'detail':'The brief was composed from its sources and kept in the local store; nothing was delivered.'}

    def delete_brief(self,body):
        if not isinstance(body,dict) or not body.get('id'):raise SourceError('Give the identifier of the kept brief')
        removed=self.briefcase_store().delete(str(body['id']))
        removed['briefs']=self.briefs()['briefs']
        return removed

    def watches(self):
        """The local watch inbox: registered requests, their states and their limits."""
        from .outbox import OutboxStore
        store=self.watch_store()
        box=OutboxStore(store.path)
        watches=store.list(now=self.clock())
        for watch in watches:
            watch['outbox_pending']=box.count_pending(watch['id'])
            delivered=[event['timestamp'] for row in box.list(watch_id=watch['id'])
                       for event in box.ledger(row['id']) if event['event']=='sent']
            watch['last_notification_at']=max(delivered) if delivered else None
        return {'schema_version':'watch-inbox-v1','delivery':'local_inbox_and_opt_in_web_push',
                'note':('Watches are evaluated only when asked. Opt-in Web Push requires a subscribed browser and a running check/dispatch process. A no-match result is not an '
                        'all-clear, and a hazard the connected official products do not carry stays recorded as not connected.'),
                'checked_products':['S15 IMD district warning product','S06 CAP relay assessment'],
                'watches':watches}

    def watch_health(self):
        """Supervision truth for the watch pipeline: last tick, freshness, queue, watchers.

        A fresh daemon heartbeat means checks are running on schedule; anything
        else is reported as manual-only or stale — never as a running service.
        """
        from .outbox import OutboxStore
        from .watches import heartbeat_status, read_heartbeat
        now=self.clock()
        store=self.watch_store()
        box=OutboxStore(store.path)
        heartbeat=read_heartbeat(store.path)
        tick=heartbeat_status(heartbeat,now=now)
        watches=store.list(now=now)
        active=[watch for watch in watches if not watch.get('expired') and watch.get('state')!='expired']
        try:plan_watcher=self.plan_watcher().status()
        except Exception:plan_watcher={'running':False}
        trigger=(heartbeat or {}).get('trigger')
        if tick['fresh'] and trigger=='daemon':
            mode='foreground-supervised'
        elif tick['fresh']:
            mode='manual-recent'
        else:
            mode='manual-only'
        return {'schema_version':'watch-health-v1',
                'mode':mode,
                'note':('No hosted daemon or OS scheduler is installed: checks run while a supervisor loop or a manual trigger fires. '
                        'A stale tick means nobody is checking watches, and queued warnings wait until the next run.'),
                'heartbeat':heartbeat,'tick':tick,
                'outbox':box.stats(now=now),
                'watches':{'total':len(watches),'active':len(active),'expired':len(watches)-len(active)},
                'plan_watcher':plan_watcher}

    def check_watches(self,body):
        """Check one watch or every open watch, in the foreground, and record the outcome."""
        from .conversation import ConversationEngine
        from .outbox import dispatch_outbox,escalate_unacked
        from .push import channel_sender
        from .watches import check_due,check_lock,check_watch
        if not isinstance(body,dict) or set(body)-{'id'}:raise ValueError('Send an optional watch id')
        if self.conversation is None:
            with self._conversation_lock:
                if self.conversation is None:self.conversation=ConversationEngine(self)
        store=self.watch_store()
        from .ratelimit import check as rate_check
        rate_check('watches/check', store.path)
        send=channel_sender(self._push_key_path(),store.path)
        if body.get('id'):
            with check_lock(store.path):
                result=check_watch(store,self.conversation,store.get(str(body['id'])),now=self.clock())
            dispatched=dispatch_outbox(store.path,now=self.clock(),send=send)
            escalated=escalate_unacked(store.path,now=self.clock())
            return {'schema_version':'watch-check-v1','delivery':'local_inbox_and_opt_in_web_push',
                    'result':result,'dispatched':dispatched,'escalated':escalated}
        results=check_due(store,self.conversation,now=self.clock())
        dispatched=dispatch_outbox(store.path,now=self.clock(),send=send)
        escalated=escalate_unacked(store.path,now=self.clock())
        from .watches import record_heartbeat
        record_heartbeat(store.path,{'trigger':'manual-api',
                                     'stale_after_seconds':3600,
                                     'checked':len(results),
                                     'enqueued':sum(1 for row in results if row.get('notification')),
                                     'dispatched':len(dispatched),
                                     'escalated':len(escalated)},now=self.clock())
        return {'schema_version':'watch-check-v1','delivery':'local_inbox_and_opt_in_web_push',
                'note':'Foreground check only; no daemon is installed. Web push delivers to subscribed browsers only.',
                'results':results,'dispatched':dispatched,'escalated':escalated}

    def outbox(self,params):
        """The notification outbox: queued, sent, failed, dead and acked rows."""
        from .outbox import OutboxStore
        params=params or {}
        def first(name):
            value=params.get(name)
            if isinstance(value,(list,tuple)):value=value[0] if value else None
            return value
        state=first('state');watch_id=first('watch_id')
        if state is not None and state not in {'created','queued','claimed','sent','failed','dead','acked','gone'}:
            raise SourceError('Unknown outbox state: '+str(state))
        store=self.watch_store()
        rows=OutboxStore(store.path).list(state=state,watch_id=watch_id)
        summaries=[{key:row[key] for key in ('id','watch_id','correlation_id','fingerprint_sha256','state','channel','created_at','updated_at','retry_count','max_retries','next_retry_at','last_error','error_class')} for row in rows]
        for summary,row in zip(summaries,rows):summary['payload']=row.get('payload') or {}
        return {'schema_version':'outbox-v1','delivery':'local_inbox_and_opt_in_web_push',
                'note':'A notification is enqueued only when a watch check observes a changed official state; delivery is recorded per channel.',
                'notifications':summaries}

    def delete_watch(self,body):
        """Retire a watch and cancel its pending notifications."""
        if not isinstance(body,dict) or not body.get('id'):raise SourceError('Give the identifier of the watch to retire')
        removed=self.watch_store().archive(str(body['id']),now=self.clock())
        removed['watches']=self.watches()['watches']
        return removed

    def set_watch_channels(self,body):
        """Replace one watch's delivery channels, keeping consent honest.

        Adding web_push requires an active push subscription for that watch (a
        bare toggle cannot invent consent); removing it drops the consent entry.
        local_inbox can never be removed.
        """
        from .push import PushStore
        if not isinstance(body,dict) or not body.get('id') or not isinstance(body.get('channels'),list):
            raise SourceError('Send the watch id and a channels list')
        store=self.watch_store()
        watch_id=str(body['id'])
        from .ratelimit import check as rate_check
        rate_check('watches/channels', store.path)
        channels=list(body['channels'])
        if 'web_push' in channels and not PushStore(store.path).active_for_watch(watch_id):
            raise SourceError('No active push subscription for this watch; subscribe this browser first')
        watch=store.set_channels(watch_id,channels,
                                 consent_source='browser_push_grant' if 'web_push' in channels else None,
                                 now=self.clock())
        return {'schema_version':'watch-channels-v1','id':watch['id'],'channels':watch['channels'],
                'consent_record':watch['consent_record'],
                'detail':'Delivery channels replaced; consent entries follow real grants only.'}

    def ack_notification(self,outbox_id,body):
        """Acknowledge a sent notification: safe, need help, evacuating or seen."""
        from .outbox import acknowledge
        if not isinstance(body,dict) or not body.get('response'):
            raise SourceError('Send one of: safe, need_help, evacuating, seen')
        from .ratelimit import check as rate_check
        rate_check('outbox/ack', self.watch_store().path)
        result=acknowledge(self.watch_store().path,str(outbox_id),str(body['response']),now=self.clock())
        result['schema_version']='outbox-ack-v1'
        return result

    def watch_dma(self,params):
        """Per-place, per-source delivery aggregate: watches, notifications, acks, help signals."""
        from .outbox import FeedbackStore,OutboxStore
        store=self.watch_store()
        box=OutboxStore(store.path)
        feedback={row['outbox_id']:row for row in FeedbackStore(store.path).list()}
        places={}
        for watch in store.list(now=self.clock()):
            name=(watch.get('place') or {}).get('name') or 'place not stated'
            entry=places.setdefault(name,{'place':name,'watches':0,'notifications':0,
                                          'acked':0,'safe':0,'need_help':0,'evacuating':0,'seen':0,
                                          'unacked':0,'sources':{}})
            entry['watches']+=1
            for row in box.list(watch_id=watch['id']):
                if row['state'] in ('created','queued','claimed','sent','failed','dead','acked','gone'):
                    entry['notifications']+=1
                    for fact in (row.get('payload') or {}).get('facts') or []:
                        source=str((fact or {}).get('source_id') or 'unknown')
                        cell=entry['sources'].setdefault(source,{'notifications':0,'acked':0})
                        cell['notifications']+=1
                        if row['state']=='acked':
                            cell['acked']+=1
                if row['state']=='acked':
                    entry['acked']+=1
                    response=(feedback.get(row['id']) or {}).get('response')
                    if response in entry:entry[response]+=1
                elif row['state']=='sent':
                    entry['unacked']+=1
        return {'schema_version':'watch-dma-v2',
                'note':'Counts of local notifications and the responses owners sent back, broken down by official source. Nothing here leaves this machine.',
                'places':sorted(places.values(),key=lambda item:item['place'])}

    def create_watch(self,body):
        """Register a watch for explicit coordinates, without chat and without guessing.

        The place is stored exactly as given: no gazetteer lookup runs here, so an
        official warning can never be attached to a wrongly resolved district. The
        hazard is read from the request the same deterministic way chat does it.
        """
        from .watches import WatchStore,connected,hazard_of
        if not isinstance(body,dict):raise SourceError('Send a place with coordinates')
        place=body.get('place') or {}
        if not isinstance(place,dict):raise SourceError('Send a place object with coordinates')
        name=place.get('name')
        try:
            latitude=float(place.get('latitude'));longitude=float(place.get('longitude'))
        except (TypeError,ValueError):raise SourceError('Give numeric latitude and longitude') from None
        if not isinstance(name,str) or not 2<=len(name.strip())<=100:
            raise SourceError('Give the place a name of 2–100 characters')
        if not (-90<=latitude<=90 and -180<=longitude<=180):
            raise SourceError('Coordinates are outside the valid ranges')
        question='Notify me if an official warning is issued for '+name.strip()
        if isinstance(body.get('hazard'),str) and body['hazard'].strip():
            question='Notify me if an official '+body['hazard'].strip()+' warning is issued for '+name.strip()
        hazard=hazard_of(question)
        store=self.watch_store()
        from .ratelimit import check as rate_check
        rate_check('watches/create', store.path)
        watch=store.create(question,{'name':name.strip(),'state':place.get('state') or '',
                                     'district':place.get('district') or '','kind':'unknown',
                                     'coordinates':{'latitude':latitude,'longitude':longitude}},
                           hazard,window_start=body.get('window_start'),window_end=body.get('window_end'),
                           now=self.clock())
        return {'schema_version':'watch-create-v1','id':watch['id'],'state':watch['state'],
                'hazard':hazard,'connected':connected(hazard),'place':watch['place'],
                'delivery':watch['delivery'],
                'detail':('Watch registered locally for explicit coordinates; it is checked only when asked.'
                          if connected(hazard) else
                          'Watch recorded, but the connected official products do not carry this hazard.')}

    def _push_key_path(self):
        return self.watch_store().path.parent/'push-vapid.json'

    def vapid_public_key(self):
        """The public VAPID key browsers subscribe with. Safe to expose."""
        from .push import vapid_keypair
        _,public=vapid_keypair(self._push_key_path())
        return {'schema_version':'push-vapid-v1','public_key':public}

    def push_state(self,params):
        """Push subscription counts: active, expired and revoked."""
        from .push import PushStore
        store=self.watch_store()
        subscriptions=PushStore(store.path)
        rows=subscriptions.purge_expired(now=self.clock())
        counts={state:len(subscriptions.list(state=state)) for state in ('active','expired','revoked')}
        return {'schema_version':'push-state-v1','delivery':'local_inbox_and_opt_in_web_push',
                'note':'Opt-in Web Push sends encrypted messages through the browser vendor push service to subscribed browsers; the local check process must be running.',
                'purged_expired':rows['retired'],'subscriptions':counts}

    def push_subscribe(self,body):
        """Store a browser push subscription, optionally bound to one watch."""
        from .push import PushStore
        if not isinstance(body,dict):raise SourceError('Send a push subscription')
        from .ratelimit import check as rate_check
        rate_check('push/subscribe', self.watch_store().path)
        keys=body.get('keys') or {}
        entry=PushStore(self.watch_store().path).subscribe(
            body.get('endpoint'),keys.get('p256dh'),keys.get('auth'),
            watch_id=body.get('watch_id'),expires_at=body.get('expirationTime'),now=self.clock())
        return {'schema_version':'push-subscription-v1','subscribed':True,'id':entry['id'],
                'watch_id':entry['watch_id'],'duplicate':bool(entry.get('duplicate')),
                'detail':('This subscription already exists.' if entry.get('duplicate')
                          else 'Stored. Bound watches gained the web_push channel with a recorded grant.' if entry.get('watch_id')
                          else 'Stored without a watch binding; enable push per watch from the inbox.')}

    def push_unsubscribe(self,body):
        """Revoke the browser push subscription for one endpoint."""
        from .push import PushStore
        if not isinstance(body,dict) or not body.get('endpoint'):raise SourceError('Send the endpoint to revoke')
        from .ratelimit import check as rate_check
        rate_check('push/unsubscribe', self.watch_store().path)
        return PushStore(self.watch_store().path).unsubscribe(str(body['endpoint']))

    # Plan Watch: plans described in chat, checked against the official district warning
    # product by a watcher that runs only while this workspace runs.
    def plan_store(self,replay=False):
        from .plans import PlanStore
        return PlanStore(self.service.ingestion_database.parent/('plans-replay.sqlite' if replay else 'plans.sqlite'))

    def plan_watcher(self):
        if getattr(self,'_plan_watcher',None) is None:
            from .plan_watcher import PlanWatcher
            self._plan_watcher=PlanWatcher(self)
        return self._plan_watcher

    def plans(self,params=None):
        """Saved plans, their notifications and the watcher state. Nothing here leaves this machine."""
        from .plan_intake import public
        value=(params or {}).get('replay')
        if isinstance(value,(list,tuple)):value=value[0] if value else ''
        replay=value in (True,'1','true')
        store=self.plan_store(replay=replay)
        now=self.clock()
        notifications=store.notifications(limit=50)
        for item in notifications:item['visible']=parsed(item['visible_at'])<=now
        return {'schema_version':'plan-inbox-v1','mode':'replay_of_recorded_editions' if replay else 'live',
                'delivery':'local_inbox_and_browser_notifications_while_the_workspace_runs',
                'plans':[public(plan) for plan in store.list()],'notifications':notifications,
                'watcher':dict(self.plan_watcher().status(),last_cycle_at=store.meta_get('last_cycle_at'),
                               last_ok_at=store.meta_get('last_ok_at'),last_error=store.meta_get('last_error') or None),
                'recorded_editions':len(recorded_editions()),
                'limits':['Plans are checked against the IMD district warning product only, every 30 minutes while WeatherGPT runs.',
                          'No warning for your watched hazards is not an all-clear, and origin authentication of the IMD service is unverified.',
                          'Flood, cyclone and sea-area plans are recorded as not connected and are never mapped onto another product.',
                          'Nothing is sent off this machine: no SMS, e-mail, push service or subscription exists.']}

    def check_plans(self,body):
        """Run one watcher cycle now, in the foreground."""
        if not isinstance(body,dict) or body:raise ValueError('Send an empty JSON object')
        return {'schema_version':'plan-check-v1','result':self.plan_watcher().run_once()}

    def update_plan(self,body):
        """Pause, resume, end or delete one saved plan."""
        from .plan_intake import public
        from .plan_watcher import LiveEditions,baseline
        if not isinstance(body,dict) or set(body)!={'id','action'}:raise ValueError('Send a plan id and an action')
        action=body['action']
        if action not in ('pause','resume','end','delete'):raise ValueError('Action must be pause, resume, end or delete')
        store=self.plan_store()
        plan=store.get(str(body['id']))
        if action=='delete':
            store.delete(plan['id'])
            return {'schema_version':'plan-update-v1','action':'deleted','plan':public(plan)}
        if action=='pause':plan=store.update(plan['id'],state='paused')
        elif action=='end':plan=store.update(plan['id'],state='ended')
        else:
            if plan.get('state')=='not_connected':raise ValueError('A not-connected plan cannot be resumed; it has no product to check')
            plan=store.update(plan['id'],state='watching',last_snapshot=None,last_ok_at=None)
            try:baseline(store,plan,LiveEditions(self.foundation()),self.clock())
            except (OSError,ValueError):pass
            plan=store.get(plan['id'])
        return {'schema_version':'plan-update-v1','action':action,'plan':public(plan)}

    def replay_plans(self,body):
        """Replay recorded IMD editions over copies of the saved plans, into the replay inbox only."""
        from .plan_watcher import replay
        if not isinstance(body,dict) or body:raise ValueError('Send an empty JSON object')
        result=replay(self.plan_store(),self.plan_store(replay=True),recorded_editions())
        return {'schema_version':'plan-replay-v1','result':result,'inbox':self.plans({'replay':True})}

    def chat_progress(self):
        """What the engine is doing now, for a page that is waiting on a turn.

        Read-only and cheap: the running turn's stage names and the gate's own queue
        counters. No question text, no completion fraction, no confidence.
        """
        if self.conversation is None:
            return {'schema_version':'chat-progress-v1','state':'idle','stage':None,'stage_label':None,
                    'stages_seen':[],'stage_since_utc':None,'stage_seconds':None,'turn_seconds':None,
                    'queue':{'waiting':0,'active':0,'capacity':None,'wait_seconds_before_refusal':None},
                    'stage_note':'No turn has run on this workspace yet.','stages_are_facts_not_progress':True,
                    'checked_at_utc':self.clock().isoformat() if hasattr(self,'clock') else None}
        return self.conversation.progress()

    def advisory_brief(self,params):
        """Compose the advisory brief: published crop advice for a district, with forecast context.

        The route asks for the district or region explicitly. It never infers which district
        bulletin to read from a coordinate, because reading the wrong district's advice is worse
        than asking one question.
        """
        from . import product_api
        from .advisory import compose

        def first(name, default=None):
            value = (params or {}).get(name)
            if isinstance(value, (list, tuple)):
                value = value[0] if value else None
            return default if value in (None, '') else value

        region = first('region')
        if not region:
            raise SourceError('Name the district or region whose published advice should be read; '
                              'the workspace will not guess one from a coordinate.')
        state = first('state')
        crop = first('crop', '')
        stage = first('stage', '')
        topic = first('topic', 'general')
        mode = first('mode', 'source_lookup')
        day = int(first('day', '1'))
        if mode not in ('source_lookup', 'decision_support'):
            raise SourceError('Use source_lookup or decision_support')
        if day not in (1, 2, 3, 5, 7):
            raise SourceError('Ask for 1, 2, 3, 5 or 7 forecast days')
        facts, window, forecast_note = [], None, 'no point was given, so no forecast context was retrieved'
        latitude, longitude = first('lat'), first('lon')
        if latitude is not None and longitude is not None:
            view = product_api.forecast(self.foundation(), float(latitude), float(longitude), days=day)
            data = view.get('data') or {}
            for name, entry in (data.get('parameters') or {}).items():
                points = (entry or {}).get('points') or []
                if not points:
                    continue
                facts.append({'parameter': name, 'value': points[0].get('v'), 'last_value': points[-1].get('v'),
                              'samples': len(points), 'unit': (entry or {}).get('unit'),
                              'place': (data.get('requested') or {}).get('label') or None,
                              'start': points[0].get('t'), 'end': points[-1].get('t'),
                              'source_id': ((view.get('sources') or [{}])[0] or {}).get('source_id'),
                              'label': name})
            window = {'days': day, 'first_valid': (facts[0]['start'] if facts else None),
                      'last_valid': (facts[0]['end'] if facts else None)}
            forecast_note = view.get('status')
        brief = compose(self.document_index(),
                        {'region': region, 'state': state, 'crop': crop, 'stage': stage, 'topic': topic,
                         'mode': mode, 'window': window, 'point': {'latitude': latitude, 'longitude': longitude}},
                        forecast=facts)
        brief['forecast_status'] = forecast_note
        brief['schema_version'] = 'advisory-brief-v1'
        brief['generated_at_utc'] = self.clock().isoformat()
        return brief

    def cancel_chat(self,body):
        """Ask a running turn to stop at its next stage boundary.

        The reply says exactly what happened: a stop was requested, or no such turn is
        running here. It never claims the server stopped if it had already finished.
        """
        import uuid
        if not isinstance(body,dict) or set(body)-{'request_id'}:raise ValueError('Send request_id')
        request_id=body.get('request_id')
        try:uuid.UUID(str(request_id))
        except (ValueError,TypeError,AttributeError):raise ValueError('Invalid request identifier')
        if self.conversation is None:
            return {'request_id':str(request_id),'state':'not_running','detail':'No turn is running on this workspace.'}
        return self.conversation.cancel(str(request_id))

    DOCUMENT_STORE=ROOT/'data/runtime/documents'

    def document_index(self):
        from .bulletin_index import BulletinIndex,EXTRACTION_VERSION
        return BulletinIndex(self.service.raw_root.parent/'bulletins'/EXTRACTION_VERSION/'index.sqlite')

    def bulletin_pdf(self,sha):
        """Serve a verified source document body from whichever corpus published it.

        Bodies are pruned after the retention window while hashes and extracted text are
        kept, so a document that is published but whose body has gone raises DocumentPruned
        and is answered with 410. An identity that was never published is a plain not-found:
        the two must not be confused, because one says 'ask again differently' and the other
        says 'this never existed here'.
        """
        from .documents import DocumentPruned
        from .transport import digest,SourceError
        if not re.fullmatch(r'[a-f0-9]{64}',sha):raise SourceError('Invalid document identity')
        index=self.document_index()
        pruned=DocumentPruned(sha,'The source document body is outside the local retention window.')
        if (index.path.parent/'publications'/(sha+'.json')).exists():
            document=index.document_body_of_chunk_publication(sha)
            if document is None:raise pruned
            body=document
        elif index.document_publications(sha):
            published=index.passage_document(sha)
            blob=(published.get('provenance') or {}).get('blob') or published.get('blob')
            if not blob:raise SourceError('Published document records no body location')
            path=(self.DOCUMENT_STORE/blob).resolve()
            if self.DOCUMENT_STORE.resolve() not in path.parents:raise SourceError('Document body path leaves its store')
            if not path.exists():raise pruned
            body=path.read_bytes()
        else:
            raise SourceError('No published document carries this identity')
        if digest(body)!=sha:raise SourceError('Document changed during read')
        return body

    def document_retention(self,sha):
        """What is still held for a document whose body has been pruned."""
        index=self.document_index()
        published=index.passage_document(sha)
        with index.connection() as db:
            pages=[r[0] for r in db.execute('SELECT DISTINCT physical_page FROM (SELECT json_extract(payload,\'$.physical_page\') AS physical_page FROM passages WHERE document_sha=?) ORDER BY physical_page',(sha,))]
            passages=db.execute('SELECT count(*) FROM passages WHERE document_sha=?',(sha,)).fetchone()[0]
        return {'sha256':sha,'family':published.get('family'),'region':published.get('region'),
                'issue_date':published.get('issue_date'),'pages':published.get('pages'),
                'retained_passages':passages,'retained_physical_pages':pages,
                'extraction_version':published.get('extraction_version')}

    # --- Spoken access (PS feature 8) -------------------------------------------
    # Audio is a rendering of an answer, or a claim about what a person said. Neither
    # is evidence, so nothing here is stored as a source or given a source identifier.
    MAX_AUDIO_UPLOAD=8_000_000
    # Above the service's own 2500-character limit on purpose, so a long answer is
    # spoken as several segments instead of being refused. A cap below that limit would
    # have made the segmenting unreachable and silently dropped nothing but useful text.
    MAX_SPEAK_CHARACTERS=6000

    def languages(self):
        """What the interface may offer, with measured support per direction."""
        from .languages import catalogue
        from . import speech
        return {'schema_version':'language-support-view-v1',
                'service_configured':speech.configured(),
                'note':('Only a measured capability is offered. A language the provider documents but '
                        'this project has not verified is shown as unmeasured, not as available.'),
                'languages':catalogue()}

    def transcribe(self, body):
        """Turn recorded speech into a transcript the user can correct before asking."""
        import base64
        from . import speech
        from .languages import normalise
        if not isinstance(body,dict) or set(body)-{'audio_base64','language','content_type'}:
            raise ValueError('Send audio_base64 and optional language or content_type')
        encoded=body.get('audio_base64')
        if not isinstance(encoded,str) or not encoded:raise ValueError('Recorded audio is required')
        if len(encoded)>self.MAX_AUDIO_UPLOAD:raise ValueError('The recording is longer than this workspace accepts')
        try:audio=base64.b64decode(encoded,validate=True)
        except (ValueError,TypeError):raise ValueError('The recording could not be decoded')
        language=normalise(body.get('language')) if body.get('language') else None
        if body.get('language') and not language:raise ValueError('Unsupported language: '+str(body.get('language')))
        content_type=body.get('content_type') or 'audio/wav'
        if not isinstance(content_type,str) or not content_type.startswith('audio/'):
            raise ValueError('content_type must name an audio format')
        heard=speech.transcribe(audio,language=language,content_type=content_type,
                                filename='question.'+content_type.split('/')[-1].split(';')[0])
        return {**heard,
                'is_evidence':False,
                'confirm_before_asking':True,
                'why_confirm':('A transcript is what the recogniser heard, not what was said. Place names '
                               'and numbers are the words it is most likely to get wrong, so read it back '
                               'before it becomes a question.')}

    def speak(self, body):
        """Speak text that has already been produced and gated. Never generates wording."""
        import base64
        from . import speech
        from .languages import normalise, supports
        if not isinstance(body,dict) or set(body)-{'text','language'}:
            raise ValueError('Send text and language')
        text=body.get('text')
        if not isinstance(text,str) or not text.strip():raise ValueError('There is no text to speak')
        if len(text)>self.MAX_SPEAK_CHARACTERS:
            raise ValueError('Text is longer than the %d characters this workspace speaks at once'%self.MAX_SPEAK_CHARACTERS)
        language=normalise(body.get('language'))
        if not language:raise ValueError('Unsupported language: '+str(body.get('language')))
        if supports(language,'speak')!='verified':
            # Refusing is the honest answer: the provider accepts every code, but this
            # project has only verified some, and unintelligible audio is worse than none.
            raise ValueError('Speech in this language has not been verified by this project, so it is not '
                             'offered. Run scripts/measure_language_support.py to test it.')
        pieces=speech.chunks(text)
        audio=[];total=0;meta=None
        for piece in pieces:
            body_bytes,meta=speech.speak(piece,language)
            audio.append(base64.b64encode(body_bytes).decode());total+=len(body_bytes)
        return {'language':language,'segments':audio,'segment_count':len(audio),'bytes':total,
                'codec':(meta or {}).get('codec','wav'),'model':(meta or {}).get('model'),
                'is_evidence':False,
                'note':'Spoken rendering of text already produced and checked. It adds no new claim.'}

    def arguments(self, body):
        if not isinstance(body,dict) or set(body)-{'question','entity_id','coordinates'}:
            raise ValueError('Use question and optional entity_id or coordinates')
        question=body.get('question')
        if not isinstance(question,str) or not 1<=len(question)<=500:raise ValueError('Enter a question of 1–500 characters')
        selection={k:body[k] for k in ('entity_id','coordinates') if k in body}
        if 'entity_id' in selection and (not isinstance(selection['entity_id'],str) or len(selection['entity_id'])!=64):
            raise ValueError('Select a valid place candidate')
        if 'coordinates' in selection:
            c=selection['coordinates']
            if not isinstance(c,dict) or set(c)!={'latitude','longitude'}:raise ValueError('Both latitude and longitude are required')
        return question,selection

    def answer(self, body):
        question,selection=self.arguments(body)
        answer=self.service.answer(question,**selection)
        return {'answer':answer,'context':context_from_answer(answer)}

    def refresh(self, body):
        packet=self.answer(body);answer=packet['answer']
        # Resolve the same user request first. Never substitute a guessed centroid.
        if not answer['request'] or (answer.get('location') or {}).get('status')!='selected_point':
            raise ValueError('Choose a place point or enter explicit coordinates before refreshing')
        now=self.clock();request=answer['request']
        if parsed(request['start_utc'])<=now:raise ValueError('Choose a future forecast interval')
        days=max(3,(parsed(request['end_utc']).date()-now.date()).days+1)
        if days>7:raise ValueError('Choose an interval within the next seven UTC calendar days')
        policy=json.loads(self.service.policy_path.read_text())
        source=policy.get('sources',{}).get('S21',{})
        registry=json.loads(self.service.registry_path.read_text())
        entry=next((p for p in registry['products'] if p['id']=='S21'),{})
        if (policy.get('schema_version')!='answer-policy-v1' or source.get('enabled') is not True
                or source.get('publication_policy')!='prototype_model_point_reference'
                or entry.get('integration',{}).get('status')!='prototype_adapter_tested'):
            raise ValueError('Forecast collection is disabled by the source policy')
        if packet['context']['status']=='eligible_prototype':
            packet['refresh']={'state':'already_fresh','provider_attempts':0,
                               'message':'The stored forecast is still within its serving lifetime.'}
            return packet
        p=answer['location']['requested_point']
        db=IngestionDB(self.service.ingestion_database,clock=self.clock)
        try:
            # One collection identity per point/horizon/hour; repeated clicks do not
            # bypass retry timing, exhausted jobs, provider cooldowns or budgets.
            cycle=now.replace(minute=0,second=0,microsecond=0).isoformat()
            jid=db.enqueue('forecast',p['latitude'],p['longitude'],days,cycle)
            before=db.db.execute('SELECT attempts FROM jobs WHERE id=?',(jid,)).fetchone()[0]
            worker=run_one(db,self.service.raw_root,self.opener,job_id=jid)
            job=dict(db.db.execute('SELECT state,attempts,due FROM jobs WHERE id=?',(jid,)).fetchone())
            # This measures claims; network reservations are independently recorded
            # by the governed opener. They are counted by job in the event ledger.
            attempts=db.db.execute("SELECT count(*) FROM events WHERE job_id=? AND kind='request_reserved'",(jid,)).fetchone()[0]
        finally:db.close()
        packet=self.answer(body)
        packet['refresh']={'state':job['state'],'job_id':jid,'worker_state':worker['state'],
                           'claims_this_action':max(0,job['attempts']-before),
                           'job_provider_attempts':attempts,'retry_due_utc_epoch':job['due'],
                           'message':('Collection completed; answer checked against the stored evidence.' if job['state']=='succeeded' else
                                      'Collection is '+job['state']+'. Retry timing and request limits remain in force; no background worker is running.')}
        return packet

    # Local retention and health read models. They expose the store to its owner
    # on loopback only; question text is never written to a log. Counts and job
    # states here are not forecast skill, coverage or operational readiness.
    def conversation_store(self):
        return self.service.ingestion_database.parent/'conversations.sqlite'

    # Product read-model surface. The Foundation shares the runtime store the rest of
    # the workspace already uses, so a cached official response is reused rather than
    # fetched again for a second view.
    def foundation(self):
        if self._foundation is None:
            from .foundation import Foundation
            from .transport import Store
            self._foundation=Foundation(Store(self.service.raw_root.parent.parent))
        return self._foundation

    def is_product(self,path):
        from . import product_api
        return path in product_api.PRODUCT_PATHS

    def product(self,path,params):
        from . import product_api
        if path not in product_api.PRODUCT_PATHS:return None
        # The HTTP handler hands over query-parameter lists (parse_qs). Internal callers - the
        # CLI scripts, tests and the engine - hand over scalars, and a scalar sliced as a list
        # silently became its first character, so every value is normalised here.
        normalised={}
        for key,value in (params or {}).items():
            if isinstance(value,(list,tuple)):normalised[key]=list(value)
            elif value is None:normalised[key]=[]
            else:normalised[key]=[str(value)]
        return product_api.dispatch(self.foundation(),path,normalised)

    def map_layer(self,name):
        from . import product_api
        return product_api.map_layer_path(name).read_bytes()

    def conversations(self,limit=40):
        path=self.conversation_store()
        limit=max(1,min(int(limit),200))
        if not path.exists():
            return {'schema_version':'conversation-ledger-v1','total':0,'limit':limit,'conversations':[],
                    'note':'No local conversation store exists yet; the first question creates it.'}
        db=sqlite3.connect(path)
        try:
            rows=db.execute('SELECT id,payload,updated FROM conversations ORDER BY updated DESC LIMIT ?',(limit,)).fetchall()
            total=db.execute('SELECT count(*) FROM conversations').fetchone()[0]
        finally:db.close()
        items=[]
        for cid,payload,updated in rows:
            try:state=json.loads(payload) if payload else {}
            except ValueError:state={}
            history=state.get('history') or []
            opening=next((turn.get('content') for turn in history if turn.get('role')=='user'),'')
            items.append({'id':cid,'updated':updated,'turns':len(history),
                          'asked':sum(1 for turn in history if turn.get('role')=='user'),
                          'opening_question':excerpt(opening)})
        return {'schema_version':'conversation-ledger-v1','total':total,'limit':limit,'conversations':items,
                'note':'Stored on this machine for the person who asked. Excerpts are served over loopback only and never written to logs.'}

    def conversation_transcript(self,cid):
        _conversation_id(cid)
        path=self.conversation_store()
        if not path.exists():raise SourceError('This conversation is not in the local store. Start a new conversation.')
        db=sqlite3.connect(path)
        try:row=db.execute('SELECT payload,updated FROM conversations WHERE id=?',(cid,)).fetchone()
        finally:db.close()
        if row is None:raise SourceError('This conversation is not in the local store. Start a new conversation.')
        try:state=json.loads(row[0]) if row[0] else {}
        except ValueError:state={}
        turns=[{'role':turn.get('role'),'content':turn.get('content')} for turn in (state.get('history') or []) if turn.get('content')]
        return {'schema_version':'conversation-transcript-v1','id':cid,'updated':row[1],'turns':turns,
                'note':'Restored transcript. Earlier answers are timestamped receipts from the moment they were retrieved; ask again before relying on one.'}

    def delete_conversation(self,cid):
        _conversation_id(cid)
        path=self.conversation_store()
        if not path.exists():raise SourceError('This conversation is not in the local store.')
        with sqlite3.connect(path) as db:removed=db.execute('DELETE FROM conversations WHERE id=?',(cid,)).rowcount
        return {'schema_version':'conversation-delete-v1','id':cid,'deleted':max(0,removed),
                'note':'Removed from the local conversation store. Saved source documents and published evidence are unaffected.'}


    def warm_layers(self, places=None):
        """Fetch the slow connected layers once, in the background, so a first ask is not the wait.

        Measured on 15 September 2026: the first right-now ask took 146 s and the first district-warning
        ask 67 s, because those layers were being read for the first time. Warming does exactly what an
        ask would do - the same governed adapters, the same cache and provenance - so the user's first
        question reads warm cache rather than an empty one. Nothing is inferred from it: a failure here
        is printed and recorded, and the ask that follows retrieves as it always did.
        """
        from . import product_api
        # A direct call (a test, a script) must work without start_warming having run first.
        if not isinstance(getattr(self, 'warm_state', None), dict):
            self.warm_state = {'state': 'warming', 'layers': [], 'finished_at_utc': None}
        self.warm_state['layers'] = list(self.warm_state.get('layers') or [])
        targets = list(places or []) or [{'latitude': 23.02579, 'longitude': 72.58727, 'label': 'the default working place'}]
        results = []
        foundation = self.foundation()
        for target in targets:
            latitude, longitude = float(target['latitude']), float(target['longitude'])
            for name, call in (
                    ('station layers', lambda: product_api.observations_bundle(foundation, latitude, longitude, limit=2)),
                    ('district warning layer', lambda: product_api.warnings_place(foundation, latitude, longitude)),
                    ('forecast product', lambda: product_api.forecast(foundation, latitude, longitude, days=1))):
                began = time.monotonic()
                try:
                    call()
                    state, detail = 'warmed', ''
                except Exception as failure:  # a warm-up is best effort and says so
                    state, detail = 'failed', str(failure)[:160]
                results.append({'layer': name, 'place': target.get('label'), 'state': state,
                                'seconds': round(time.monotonic() - began, 1), 'detail': detail})
                self.warm_state['layers'] = list(results)  # progress a reader can watch, not a spinner
        self.warm_state = {'state': 'done' if all(item['state'] == 'warmed' for item in results) else 'partial',
                           'layers': results, 'finished_at_utc': self.clock().isoformat()}
        return self.warm_state

    def start_warming(self, places=None):
        """Warm the layers in a daemon thread; the server serves while they are being read."""
        self.warm_state = {'state': 'warming', 'layers': [], 'finished_at_utc': None}

        def run():
            try:
                self.warm_layers(places)
            except Exception as failure:
                self.warm_state = {'state': 'failed', 'layers': [], 'finished_at_utc': stamp(self.clock()),
                                   'detail': str(failure)[:200]}
                self.warm_state['finished_at_utc'] = self.clock().isoformat()

        thread = threading.Thread(target=run, name='layer-warmup', daemon=True)
        thread.start()
        return self.warm_state
    def health(self):
        # Streams are pseudonymous point identities, so this reports what was
        # collected and when, never which coordinates made up a stream.
        database=self.service.ingestion_database
        if not database.exists():
            return {'schema_version':'source-health-v1','available':False,'products':[],'job_states':{},'active_leases':0,'cooldowns':[],'total_jobs':0,'streams':0,
                    'note':'No ingestion store exists yet, so there is no collection history to report.',
                    'warm':getattr(self,'warm_state',None)}
        now=time.time()
        db=sqlite3.connect(database)
        try:
            specs=db.execute('SELECT id,spec,state FROM jobs').fetchall()
            commits=dict((job_id,committed) for job_id,committed in db.execute('SELECT job_id,committed FROM versions'))
            job_states=dict(db.execute('SELECT state,count(*) FROM jobs GROUP BY state').fetchall())
            streams=db.execute('SELECT count(DISTINCT stream) FROM jobs').fetchone()[0]
            leases=db.execute('SELECT count(*) FROM requests WHERE finished=0 AND lease_until>?',(now,)).fetchone()[0]
            cooldowns=db.execute('SELECT provider,until FROM cooldowns WHERE until>? ORDER BY until',(now,)).fetchall()
        finally:db.close()
        products={}
        for job_id,spec,state in specs:
            try:product=(json.loads(spec) or {}).get('product') or 'unlabelled'
            except (TypeError,ValueError):product='unlabelled'
            entry=products.setdefault(product,{'product':product,'jobs':0,'states':{},'newest_commit_utc':None})
            entry['jobs']+=1;entry['states'][state]=entry['states'].get(state,0)+1
            committed=commits.get(job_id)
            if committed is not None:
                stamp_value=stamp(committed)
                if entry['newest_commit_utc'] is None or committed>entry['newest_commit_utc_value']:
                    entry['newest_commit_utc']=stamp_value;entry['newest_commit_utc_value']=committed
        for entry in products.values():entry.pop('newest_commit_utc_value',None)
        return {'schema_version':'source-health-v1','available':True,
                'warm':getattr(self,'warm_state',None),
                'products':sorted(products.values(),key=lambda entry:entry['product']),
                'job_states':job_states,'total_jobs':len(specs),'streams':streams,'active_leases':leases,
                'cooldowns':[{'provider':provider,'until_utc':stamp(until)} for provider,until in cooldowns],
                'note':'Read-only projection of the local ingestion store: which products were collected, what happened to those jobs, and when the newest evidence was committed. A stream is a pseudonymous point identity, so no requested location is shown here. These counts are not coverage, forecast skill or operational readiness.'}


RECORDED_EDITIONS=ROOT/'research/implementation/plan-watch-editions'


def recorded_editions(folder=None):
    """Editions saved by scripts/capture_warning_edition.py, oldest first."""
    folder=Path(folder or RECORDED_EDITIONS)
    return sorted(folder.glob('edition-*.json')) if folder.exists() else []


def excerpt(text,limit=96):
    text=' '.join(str(text or '').split())
    return text if len(text)<=limit else text[:limit-1].rstrip()+'\u2026'


def stamp(value):
    if value is None:return None
    return datetime.fromtimestamp(float(value),timezone.utc).isoformat()


def _conversation_id(cid):
    import uuid
    try:uuid.UUID(cid)
    except (ValueError,TypeError,AttributeError):raise SourceError('Invalid conversation identifier')


def parse_ack_path(path):
    """The outbox id of POST /api/outbox/<id>/ack, else None. Query strings never match."""
    parts=(path or '').split('/')
    if len(parts)==5 and parts[1]=='api' and parts[2]=='outbox' and parts[3] and parts[4]=='ack':
        return parts[3]
    return None


# The page policy. Scripts are never inline and nothing is loaded from a CDN. The React build adds
# one relaxation, style-src-attr, because component libraries position and virtualise through style
# attributes; injected <style> elements stay blocked. This is scoped to the React surface and the
# vanilla frontend keeps the strict policy, so the change is visible and reversible.
STRICT_CSP=("default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; "
            "media-src 'self' blob: data:; frame-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
# The React surface was planned to need style-src-attr 'unsafe-inline' for component positioning and
# virtualisation. Measured in R0 (research/reviews/frontend-react-r0-20260917/csp-probe.json): Radix, TanStack
# Virtual and Motion all end up with the computed styles they need under this strict policy, because React
# writes styles through the CSSOM at runtime, which CSP does not police. No relaxation is applied; the audit
# keeps the built HTML free of markup-level style attributes.
REACT_CSP=STRICT_CSP
REACT_ASSET_TYPES={'.js':'text/javascript','.css':'text/css','.map':'application/json','.woff2':'font/woff2',
                   '.svg':'image/svg+xml','.png':'image/png','.webp':'image/webp','.json':'application/json'}


def post_routes(workspace):
    """The POST route table, at module scope so a test and the surface audit can read it.

    The table used to live inside the request handler, where only the server could see it: a route could then
    exist without any test being able to enumerate it, and a rail entry could point at a route nobody served.
    """
    return {'/api/answer':workspace.answer,'/api/refresh':workspace.refresh,'/api/chat':workspace.chat,
            '/api/chat/preview':workspace.chat_preview,
            '/api/chat/cancel':workspace.cancel_chat,'/api/watches/check':workspace.check_watches,'/api/watches/delete':workspace.delete_watch,'/api/watches/channels':workspace.set_watch_channels,'/api/watches/create':workspace.create_watch,'/api/warm':workspace.warm,
            '/api/briefing/run':workspace.run_briefing,
            '/api/plans/check':workspace.check_plans,'/api/plans/update':workspace.update_plan,'/api/plans/replay':workspace.replay_plans,
            '/api/briefs/save':workspace.save_brief,
            '/api/briefs/delete':workspace.delete_brief,
            '/api/push/subscribe':workspace.push_subscribe,'/api/push/unsubscribe':workspace.push_unsubscribe,
            '/api/speech/transcribe':workspace.transcribe,'/api/speech/speak':workspace.speak}


def make_server(workspace, port=8765):
    token=secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass  # Do not log private questions or coordinates.

        def respond(self, code, data, kind='application/json', filename=None, csp=None, cache=None):
            if kind=='application/json':data=json.dumps(data,ensure_ascii=False,allow_nan=False).encode()
            elif isinstance(data,str):data=data.encode()
            self.send_response(code)
            self.send_header('Content-Type',kind+'; charset=utf-8')
            if filename:self.send_header('Content-Disposition','attachment; filename="'+filename+'"')
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control',cache or 'no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',csp or STRICT_CSP)
            self.end_headers();self.wfile.write(data)

        def allowed_host(self):
            return self.headers.get('Host')=='127.0.0.1:'+str(self.server.server_port)

        def authorized(self):
            return hmac.compare_digest(self.headers.get('X-WeatherGPT-Token',''),token)

        def do_GET(self):
            if not self.allowed_host():return self.respond(403,{'error':'Use the loopback URL printed by the server'})
            path=urlsplit(self.path).path
            if path.startswith('/api/documents/'):
                sha=path.removeprefix('/api/documents/')
                try:return self.respond(200,workspace.bulletin_pdf(sha),'application/pdf')
                except DocumentPruned as pruned:
                    # The document is known and its passages are still indexed; only the
                    # body is outside the retention window. Say that rather than 404.
                    payload={'error':pruned.detail,
                             'retention_days':RETENTION_DAYS,
                             'retained':'the document hash and its extracted pages remain indexed and citable',
                             'sha256':pruned.sha}
                    try:payload['document']=workspace.document_retention(pruned.sha)
                    except (ValueError,OSError,KeyError,sqlite3.Error,SourceError):pass
                    return self.respond(410,payload)
                except (ValueError,OSError,KeyError,sqlite3.Error):return self.respond(404,{'error':'Verified source document is unavailable'})
            # Stored conversations and collection health are the owner's data, so they
            # require the session token as well as the loopback Host check. Any other
            # API path keeps the existing 404 behaviour.
            if path.startswith('/api/'):
                known=(workspace.is_product(path) or path=='/api/conversations' or path=='/api/health'
                       or path=='/api/languages' or path=='/api/watches' or path=='/api/watches/dma' or path=='/api/outbox' or path=='/api/plans' or path=='/api/chat/progress'
                        or path=='/api/push/vapid-key' or path=='/api/push/state' or path=='/api/watch-health'
                       or path=='/api/advisories/brief' or path=='/api/briefs' or path=='/api/briefing/latest'
                       or path.startswith('/api/briefs/')
                       or path.startswith('/api/conversations/') or path.startswith('/api/map/static/'))
                if not known:return self.respond(404,{'error':'Not found'})
                if not self.authorized():return self.respond(403,{'error':'Reload this local workspace before reading stored data'})
                try:
                    if path=='/api/conversations':return self.respond(200,workspace.conversations())
                    if path=='/api/health':return self.respond(200,workspace.health())
                    if path=='/api/languages':return self.respond(200,workspace.languages())
                    if path=='/api/watches':return self.respond(200,workspace.watches())
                    if path=='/api/watches/dma':return self.respond(200,workspace.watch_dma(parse_qs(urlsplit(self.path).query)))
                    if path=='/api/outbox':return self.respond(200,workspace.outbox(parse_qs(urlsplit(self.path).query)))
                    if path=='/api/push/vapid-key':return self.respond(200,workspace.vapid_public_key())
                    if path=='/api/push/state':return self.respond(200,workspace.push_state(parse_qs(urlsplit(self.path).query)))
                    if path=='/api/watch-health':return self.respond(200,workspace.watch_health())
                    if path=='/api/plans':return self.respond(200,workspace.plans(parse_qs(urlsplit(self.path).query)))
                    if path=='/api/chat/progress':return self.respond(200,workspace.chat_progress())
                    if path=='/api/advisories/brief':return self.respond(200,workspace.advisory_brief(parse_qs(urlsplit(self.path).query)))
                    if path=='/api/briefing/latest':return self.respond(200,workspace.latest_briefing())
                    if path=='/api/briefs':return self.respond(200,workspace.briefs())
                    if path in ('/api/briefs/get','/api/briefs/export'):
                        brief_id=(parse_qs(urlsplit(self.path).query).get('id') or [''])[0]
                        if not brief_id:raise ValueError('Give the identifier of the kept brief')
                        if path=='/api/briefs/get':return self.respond(200,workspace.saved_brief(brief_id))
                        name,text=workspace.brief_export(brief_id)
                        return self.respond(200,text,'text/markdown',filename=name)
                    if path.startswith('/api/conversations/'):return self.respond(200,workspace.conversation_transcript(path.removeprefix('/api/conversations/')))
                    if path.startswith('/api/map/static/'):
                        return self.respond(200,workspace.map_layer(path.removeprefix('/api/map/static/')),'application/geo+json')
                    view=workspace.product(path,parse_qs(urlsplit(self.path).query))
                    if view is None:return self.respond(404,{'error':'Not found'})
                    return self.respond(200,view)
                except ValueError as exc:return self.respond(400,{'error':str(exc)})
                except (OSError,sqlite3.Error):return self.respond(503,{'error':'The local evidence store is unavailable. Check its files and retry.'})
            if getattr(workspace,'frontend','react')=='react':
                # The React build: one HTML entry with the session token injected, and the hashed
                # assets beside it. A missing build is refused in words, never served as a blank page.
                import re as _re
                root=ROOT/'web'/'dist'
                if path in {'/','/index.html','/probe.html'}:
                    page=root/('probe.html' if path=='/probe.html' else 'index.html')
                    if not page.exists():
                        return self.respond(503,'The React frontend has not been built. Run: cd frontend && npm install && npm run build.','text/plain')
                    return self.respond(200,page.read_text().replace('__WORKSPACE_TOKEN__',token),'text/html',csp=REACT_CSP)
                # Two vanilla files are served to the React build from their one tracked copy rather than
                # bundled, because a vanilla check covers each of them and that check must keep covering the
                # code a React surface uses: web/viz.js (the chart engine a chart block draws with) and
                # web/sw.js (the notification worker the plans panel registers for push). Neither is
                # content-hashed, so neither is cached immutably: a change must be picked up on reload.
                if path in ('/viz.js','/sw.js'):
                    name='viz.js' if path=='/viz.js' else 'sw.js'
                    kind='text/javascript' if path=='/viz.js' else 'application/javascript'
                    engine=ROOT/'web'/name
                    if not engine.exists():
                        return self.respond(404,{'error':'This workspace file is missing; restart the workspace from a complete checkout.'})
                    return self.respond(200,engine.read_text(),kind,csp=REACT_CSP)
                asset=_re.fullmatch(r'/assets/([A-Za-z0-9._-]+)',path)
                if asset:
                    target=(root/'assets'/asset[1]).resolve()
                    if root.resolve() not in target.parents or not target.exists():
                        return self.respond(404,{'error':'Not found'})
                    return self.respond(200,target.read_bytes(),REACT_ASSET_TYPES.get(target.suffix,'application/octet-stream'),
                                        csp=REACT_CSP,cache='public, max-age=31536000, immutable')
            # The vanilla surface was removed in R6. Everything a reader can reach is served from
            # web/dist above, with the chart engine and the notification worker from their tracked copies.
            return self.respond(404,{'error':'Not found'})

        def do_DELETE(self):
            if not self.allowed_host() or not self.authorized():
                return self.respond(403,{'error':'Reload this local workspace before deleting a stored conversation'})
            path=urlsplit(self.path).path
            if not path.startswith('/api/conversations/'):return self.respond(404,{'error':'Not found'})
            try:return self.respond(200,workspace.delete_conversation(path.removeprefix('/api/conversations/')))
            except ValueError as exc:return self.respond(400,{'error':str(exc)})
            except (OSError,sqlite3.Error):return self.respond(503,{'error':'The local evidence store is unavailable. Check its files and retry.'})

        def do_POST(self):
            origin='http://127.0.0.1:'+str(self.server.server_port)
            supplied=self.headers.get('X-WeatherGPT-Token','')
            if (not self.allowed_host() or self.headers.get('Origin',origin)!=origin
                    or not hmac.compare_digest(supplied,token)):
                return self.respond(403,{'error':'Reload this local workspace before sending a request'})
            routes=post_routes(workspace)
            outbox_id=parse_ack_path(self.path)
            if self.path not in routes and outbox_id is None:return self.respond(404,{'error':'Not found'})
            # A recording is far larger than a question, so it gets its own limit rather
            # than raising the limit for every request.
            cap=11_000_000 if self.path=='/api/speech/transcribe' else 8192
            try:
                if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('Send JSON')
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=cap:raise ValueError('Request must be 1–%d bytes'%cap)
                body=json.loads(self.rfile.read(length),parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Non-finite JSON')))
                if outbox_id is not None:self.respond(200,workspace.ack_notification(outbox_id,body))
                else:self.respond(200,routes[self.path](body))
            except LanguageServiceUnavailable as exc:self.respond(503,{'error':str(exc)})
            except RateLimited as exc:self.respond(429,{'error':str(exc)})
            except (ValueError,TypeError,KeyError) as exc:self.respond(400,{'error':str(exc)})
            except (OSError,sqlite3.Error):self.respond(503,{'error':'The local evidence store is unavailable. Check its files and retry.'})

    return ThreadingHTTPServer(('127.0.0.1',port),Handler)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int,default=8765)
    p.add_argument('--database',type=Path,default=DEFAULT_DATABASE)
    p.add_argument('--raw-root',type=Path,default=DEFAULT_RAW)
    p.add_argument('--geography-database',type=Path,default=DEFAULT_GEOGRAPHY)
    p.add_argument('--no-warm',action='store_true',help='do not read the slow layers once at startup')
    p.add_argument('--no-plan-watcher',action='store_true',help='Do not check saved plans in the background')
    p.add_argument('--frontend',choices=['legacy','react'],default='react',
                   help="react serves the built web/dist bundle (the only surface since R6); 'legacy' is "
                        "refused in words rather than served")
    a=p.parse_args()
    if a.frontend!='react':
        print('The legacy web/*.js frontend was removed in R6 (docs/92): this workspace serves the built'
              ' React frontend only. Run without --frontend, or with --frontend react.',flush=True)
        raise SystemExit(2)
    workspace=Workspace(a.database,a.raw_root,a.geography_database,frontend=a.frontend)
    if not a.no_warm:workspace.start_warming()
    server=make_server(workspace,a.port)
    print('WeatherGPT: http://127.0.0.1:'+str(server.server_port)+' — local prototype; Ctrl-C to stop.',flush=True)
    print('Frontend: react (web/dist, the only surface since R6)',flush=True)
    if not a.no_plan_watcher:
        workspace.plan_watcher().start()
        print('Plan Watch: saved plans are checked every 30 minutes while this process runs.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:
        workspace.plan_watcher().stop()
        server.server_close()

if __name__=='__main__':main()
