"""Shared provider reservations for fixed document and warning GET routes."""
import fcntl,urllib.request,urllib.error,time
from contextlib import contextmanager
from urllib.parse import urlparse,parse_qs
from .ingestion import NoRedirect,retry_after,epoch,IngestionDB
from .transport import Store,SourceError

class EvidenceOpener:
    def __init__(self,db,provider,opener=None):self.db=db;self.provider=provider;self.opener=opener or urllib.request.build_opener(NoRedirect()).open;self.deadline=time.monotonic()+(12 if provider=='imd_cap' else 18)
    @contextmanager
    def __call__(self,request,timeout=25):
        remaining=self.deadline-time.monotonic()
        if remaining<=0:raise SourceError('Source retrieval time budget exhausted; remaining documents were not fetched')
        timeout=min(timeout,5,remaining)
        u=urlparse(request.full_url)
        if u.scheme!='https' or request.get_method()!='GET':raise SourceError('Evidence transport permits HTTPS GET only')
        if self.provider not in {'imd_bulletins','imd_cap'}:raise SourceError('Unregistered evidence provider')
        if self.provider=='imd_bulletins':
            allowed=(u.netloc=='mausam.imd.gov.in' and (u.path in {'/responsive/agromet_adv_ser_district_current_en.php','/responsive/agrometinformation/district_current_en_get.php'} or u.path.endswith('.pdf'))) or (u.netloc=='imdagrimet.gov.in' and u.path=='/Services/DistrictBulletin.php')
        else:
            allowed=(u.netloc=='cap-sources.s3.amazonaws.com' and u.path.startswith('/in-imd-en/') and u.path.endswith('.xml')) or (u.netloc=='reactjs.imd.gov.in' and u.path=='/geoserver/wfs')
        if not allowed:raise SourceError('URL is outside the source evidence contract')
        lock=self.db.path.with_suffix('.'+self.provider+'.lock').open('a')
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:lock.close();raise SourceError('Another retrieval from this provider is running')
        try:reservation=self.db.reserve(provider=self.provider,limits=((60,20),(3600,100),(86400,500)))
        except BaseException:lock.close();raise
        cooldown=None
        try:
            with self.opener(request,timeout=timeout) as r:yield r
        except urllib.error.HTTPError as e:
            if e.code==429 or e.code>=500:cooldown=max(retry_after(e.headers.get('Retry-After') if e.headers else None,self.db.clock()) or 0,epoch(self.db.clock())+60)
            raise SourceError('Evidence source HTTP '+str(e.code)) from e
        finally:
            try:self.db.release(reservation,cooldown)
            finally:lock.close()

@contextmanager
def evidence_store(workspace,provider,root):
    db=IngestionDB(workspace.service.ingestion_database,clock=workspace.clock)
    try:yield Store(root,clock=workspace.clock,opener=EvidenceOpener(db,provider,workspace.opener))
    finally:db.close()
