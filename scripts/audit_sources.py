#!/usr/bin/env python3
"""Audit every registered source address and compile the activation ledger.

Reads data/registry/sources.json, probes each registered address with a bounded
request, reconciles the measurement with the curated classification below, and
writes data/registry/source-review.json plus evidence files.

Usage:
    python3 scripts/audit_sources.py --offline            # rebuild the ledger without probing
    python3 scripts/audit_sources.py --only S07,S08,S58   # probe a subset
    python3 scripts/audit_sources.py --apply              # also stamp sources.json review fields
"""

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(ROOT, 'data', 'registry', 'sources.json')
LEDGER = os.path.join(ROOT, 'data', 'registry', 'source-review.json')
EVIDENCE_ROOT = os.path.join(ROOT, 'research', 'discovery', 'evidence')

SCHEMA_VERSION = 'source-review-v1'

sys.path.insert(0, ROOT)
from weathergpt_data.document_ingest import DISTRICT_SPEC, FAMILIES  # noqa: E402
from weathergpt_data.capabilities import corpus_sources  # noqa: E402

# Which sources a registered document family actually ingests. Derived from the code
# so the ledger cannot drift from it: adding a family updates the ledger on the next
# rebuild rather than leaving a stale "not connected" behind.
INGESTED_BY_FAMILY = {}
for _name, _spec in list(FAMILIES.items()) + [(DISTRICT_SPEC['family'], DISTRICT_SPEC)]:
    INGESTED_BY_FAMILY.setdefault(_spec['source_id'], []).append(_name)

# Which ingested sources an ordinary conversation can reach. Derived from the declared
# capability, not curated by hand: the whole-document tool searches by family and
# region, so a newly registered family becomes conversational on rebuild. This is the
# same drift the ledger was rebuilt to remove, applied to reachability.
CORPUS_SOURCES = set(corpus_sources())
UA = 'WeatherGPT-local-prototype/1.0 (source activation audit; local prototype use)'
TIMEOUT = 20.0
SAMPLE_CAP = 65536
SAVE_BODY_CAP = 8192

STATUS_MEANINGS = {
    'active': 'A normal user journey fetches this through a governed connector and the probe answers.',
    'active_via': 'The registered address is a page or catalogue, but the product class is already delivered by another registered source.',
    'reachable_not_connected': 'The exact registered address returns a real payload; no connector uses it yet.',
    'blocked_access': 'The registered address refuses access (credential, key or licence gate).',
    'stale_endpoint': 'The host answers but not with the registered product.',
    'not_a_data_product': 'The registered address is a catalogue, interface or documentation page rather than a retrievable payload.',
    'address_missing': 'No usable registered address; the entry is an index lead.',
    'not_a_source': 'The entry records a coverage gap or user-supplied context, not a retrievable source.',
    'unmeasured': 'No measurement has been taken for this address yet.',
    'product_address_pending': 'The registered address answers as a portal or index; the retrievable product address behind it is not yet registered.',
}

KIND_MEANINGS = {
    'point': 'coordinate or station point product',
    'document': 'published document (PDF or HTML) extracted into the bulletin index',
    'layer': 'geospatial feature layer (WFS or WMS)',
    'catalogue': 'search or index service',
    'local_snapshot': 'checksummed local snapshot already registered',
    'reference': 'codes and definitions encoded in code',
    'none': 'no connector',
}

# Curated classification. The probe measurement overrides status where the
# measurement is decisive; see reconcile().
C = {
    'S01': dict(status='blocked_access', kind='none', connected=False,
                limits=['Registered discovery address returns 401 without credentials.'],
                action='Request an IMD API key and register the served endpoint once granted.'),
    'S02': dict(status='blocked_access', kind='none', connected=False, via='S62',
                limits=['Registered discovery address returns 401 without credentials.',
                        'City forecast text is currently delivered through the S62/S21 point output, not IMD wording.'],
                action='Request an IMD API key; keep S62 as the interim city forecast supply.'),
    'S03': dict(status='blocked_access', kind='none', connected=False, via='S15',
                limits=['Registered discovery address returns 401 without credentials.',
                        'Nowcast features are delivered through the S15 WFS layer imd:NowcastWarningDistrict.'],
                action='Request an IMD API key; record which products the S15 layer does not cover.'),
    'S04': dict(status='blocked_access', kind='none', connected=False, via='S15',
                limits=['Registered discovery address returns 401 without credentials.',
                        'District warnings are delivered through the S15 WFS layer imd:district_warnings_india (764 features).'],
                action='Request an IMD API key; the S15 layer remains the warning supply.'),
    'S05': dict(status='blocked_access', kind='none', connected=False, via='S63',
                limits=['Registered discovery address returns 401 without credentials.',
                        'Place-to-forecast mapping is currently built from the S63 basemap and S24 geocoding.'],
                action='Request an IMD API key; no substitute carries IMD city identifiers yet.'),
    'S06': dict(status='active', kind='catalogue', connected=True,
                limits=['Feed entries are hazard headlines; each item still needs its own geometry and validity.'],
                action='Keep as a cross-check for warning dissemination; never as the warning level itself.'),
    'S07': dict(status='reachable_not_connected', kind='document', connected=False,
                limits=['One state composite PDF; the filename carries no issue date.'],
                action='Add to the daily document family list as a state composite agromet bulletin.'),
    'S08': dict(status='reachable_not_connected', kind='document', connected=False,
                limits=['One state district forecast and warning PDF; the filename carries no issue date.'],
                action='Add to the daily document family list as a state district bulletin.'),
    'S09': dict(status='product_address_pending', kind='document', connected=False, via='S57',
                limits=['Registered address is the advisory interface, not the advisory payload.',
                        'S57 already delivers the district farmer bulletin in English and local languages.'],
                action='Discover the crop-specific advisory route behind this page before registering it.'),
    'S10': dict(status='not_a_data_product', kind='none', connected=False, via='S15',
                limits=['Regional homepage; the underlying city forecast link is a page, not a payload.'],
                action='No connector; keep as discovery evidence for regional bulletin routes.'),
    'S11': dict(status='not_a_data_product', kind='none', connected=False,
                limits=['Catalogue page for 0.25 degree gridded rainfall NetCDF files.',
                        'Interim TLS handshake timeouts were observed on this host; the same request succeeded on a later attempt.'],
                action='Register the direct NetCDF address if a licence-free path exists, else keep as documentation.'),
    'S12': dict(status='active_via', kind='none', connected=False, via='S21',
                limits=['Product page, not an endpoint.',
                        'GFS fields already arrive through the S21 Open-Meteo GFS route.'],
                action='No connector; record that GFS fields are indirect Open-Meteo deliveries.'),
    'S13': dict(status='not_a_data_product', kind='none', connected=False, via='S22',
                limits=['Dataset page requiring a CDS account and API key.',
                        'ERA5 fields already arrive through the S22 archive route.'],
                action='No connector; ERA5 is indirect through S22.'),
    'S14': dict(status='address_missing', kind='none', connected=False,
                limits=['Entry records a selected-away mapping option; no address registered.'],
                action='Keep closed; the S63 basemap and the local gazetteer cover this need.'),
    'S15': dict(status='active', kind='layer', connected=True,
                limits=['Warning level and hazard codes are IMD-defined; colour and day windows are derived.',
                        'CAP reference resolution never authorises dissemination.'],
                action='Keep as the district warning supply; watch for schema drift.'),
    'S16': dict(status='reachable_not_connected', kind='point', connected=False,
                limits=['The registered table name answers, so an earlier "invalid table name" sample was a request error, not a dead route.',
                        'Arrays carry the string NaN as a missing-value sentinel; it must never become a value.',
                        'The date parameter names a model run, so a connector must drive it from the current run, not a fixed sample.'],
                action='Register a Mausamgram ensemble connector; it is the only multi-model source in the registry.'),
    'S17': dict(status='reachable_not_connected', kind='point', connected=False,
                limits=['The registered route answers with real arrays for the requested date.',
                        'Arrays carry the string NaN as a missing-value sentinel; it must never become a value.',
                        'Real-time bias-corrected output is not a bias-corrected forecast for the user.'],
                action='Register a Mausamgram real-time connector for cross-model comparison.'),
    'S18': dict(status='active', kind='point', connected=True,
                limits=['Station METAR only; reports the aerodrome, not the surrounding district.'],
                action='Keep for aviation and as an independent cross-check on point forecasts.'),
    'S19': dict(status='active', kind='point', connected=True,
                limits=['Aerodrome forecast, not a district forecast.'],
                action='Keep for aviation.'),
    'S20': dict(status='active', kind='point', connected=True,
                limits=['Station metadata may lag aerodrome changes.'],
                action='Keep for station identity and coordinates.'),
    'S21': dict(status='active', kind='point', connected=True,
                limits=['Model output interpolated to a point; not an observation and not an official warning.'],
                action='Keep as the land forecast supply; keep the point distance and grid basis attached.'),
    'S22': dict(status='active', kind='point', connected=True,
                limits=['Reanalysis product with a multi-day publication delay; not a live observation.'],
                action='Keep for local history and climate context.'),
    'S23': dict(status='active_via', kind='point', connected=False,
                limits=['Missing-value sentinel -999.0 must never become a value.',
                        'Community AG parameters are model and reanalysis based.'],
                action='Register a governed point connector; it adds radiation, humidity and wind parameters no current route serves.'),
    'S24': dict(status='active', kind='catalogue', connected=True,
                limits=['Place names are third-party; population and ambiguity are not district truth.'],
                action='Keep for place resolution.'),
    'S25': dict(status='active', kind='local_snapshot', connected=True,
                limits=['Supplied CSV snapshot; the published page is provenance, not a live feed.'],
                action='Keep as registered historical evidence.'),
    'S26': dict(status='active', kind='local_snapshot', connected=True,
                limits=['Supplied CSV snapshot; the published page is provenance, not a live feed.'],
                action='Keep as registered historical evidence.'),
    'S27': dict(status='active', kind='local_snapshot', connected=True,
                limits=['District cells were reconciled against a published source; reconciliation is not a re-download.'],
                action='Keep as the supplied district history.'),
    'S28': dict(status='active_via', kind='document', connected=False,
                limits=['Annual reference volume; no issue cadence within the year.'],
                action='Register the ephemeris volume as a document family if sunrise, moonrise or tide context is needed.'),
    'S29': dict(status='not_a_data_product', kind='none', connected=False, via='S21',
                limits=['Catalogue page; ECMWF open data is distributed as GRIB, which the dependency-free stack cannot decode.'],
                action='No connector; keep as a named limitation on which models are directly decoded.'),
    'S30': dict(status='not_a_data_product', kind='none', connected=False,
                limits=['Download API documentation; satellite retrieval needs a MOSDAC account.'],
                action='Record as blocked by account, not by capability.'),
    'S31': dict(status='not_a_data_product', kind='none', connected=False,
                limits=['Product page; IMERG retrieval needs an Earthdata login.'],
                action='Record as blocked by account; keep the satellite precipitation gap open.'),
    'S32': dict(status='product_address_pending', kind='document', connected=False,
                limits=['Portal only; the exact flood forecast feed is not registered.'],
                action='Discover the CWC advisory or forecast route; S37 GloFAS is the current stand-in.'),
    'S33': dict(status='product_address_pending', kind='document', connected=False,
                limits=['Portal only; the exact INCOIS product is not registered.'],
                action='Discover the INCOIS bulletin or forecast route.'),
    'S34': dict(status='product_address_pending', kind='document', connected=False,
                limits=['District contingency plans are seasonal documents, not daily advisories.'],
                action='Register the plan index as a seasonal document family for crop advisories.'),
    'S35': dict(status='not_a_data_product', kind='catalogue', connected=False,
                limits=['Catalogue page; the directory behind it is the useful artefact.'],
                action='Register the LGD district directory download for the dated alias crosswalk.'),
    'S36': dict(status='not_a_data_product', kind='none', connected=False, via='S21',
                limits=['Documentation page; single-run delivery is not registered.'],
                action='No connector; model-run identity stays with the S21/S62 metadata.'),
    'S37': dict(status='active', kind='point', connected=True,
                limits=['Modelled discharge, never an observed water level, gauge reading or warning level.'],
                action='Keep; always name the answering cell and its distance.'),
    'S38': dict(status='not_a_data_product', kind='none', connected=False,
                limits=['Catalogue of speech and translation models; access needs credentials.'],
                action='Record as blocked by credentials; the multilingual requirement depends on it.'),
    'S39': dict(status='blocked_access', kind='none', connected=False, via='S63',
                limits=['Registered discovery address returns 401 without credentials.',
                        'Station observations are delivered through the S63 layer imd:aws_data_layer.',
                        'The AWS time field is a 1970 placeholder; observation instants come from dat and update_time.'],
                action='Request an IMD API key; the S63 layer remains the station supply.'),
    'S40': dict(status='blocked_access', kind='none', connected=False, via='S63',
                limits=['Registered discovery address returns 401 without credentials.',
                        'Station identity and coordinates arrive through the S63 layer.'],
                action='Request an IMD API key; no substitute carries IMD station identifiers.'),
    'S41': dict(status='blocked_access', kind='none', connected=False,
                limits=['Registered discovery address returns 401 without credentials.',
                        'No substitute currently serves rainfall departures or district rainfall monitoring.'],
                action='Request an IMD API key; this is the largest single gap on the agriculture and flood journeys.'),
    'S42': dict(status='blocked_access', kind='none', connected=False, via='S63',
                limits=['Registered discovery address returns 401 without credentials.',
                        'Basin precipitation forecasts are delivered through the S63 layer imd:indian_river_basin (220 sub-basins).',
                        'The day1 to day3 fields are verbatim; their meaning is not interpreted.'],
                action='Request an IMD API key; keep the basin layer as the supply.'),
    'S43': dict(status='blocked_access', kind='none', connected=False, via='S63',
                limits=['Registered discovery address returns 401 without credentials.',
                        'Cyclone track is delivered through the S63 layer imd:Cyclone_Track_V.'],
                action='Request an IMD API key; keep the track layer as the supply.'),
    'S44': dict(status='blocked_access', kind='none', connected=False,
                limits=['Registered discovery address returns 401 without credentials.',
                        'Wind warning polygons have no substitute; they carry cyclone warning area.'],
                action='Request an IMD API key; record the cyclone warning gap while unconnected.'),
    'S45': dict(status='blocked_access', kind='none', connected=False,
                limits=['Registered discovery address returns 401 without credentials.'],
                action='Request an IMD API key; cone geometry has no substitute.'),
    'S46': dict(status='address_missing', kind='none', connected=False,
                limits=['Index lead only; radar imagery is not connected.',
                        'Radar station status is delivered separately through S63.'],
                action='Discover the radar image route before registering it.'),
    'S47': dict(status='address_missing', kind='none', connected=False,
                limits=['Index lead only; lightning strike data is not connected.'],
                action='Discover the lightning data route before registering it.'),
    'S48': dict(status='not_a_data_product', kind='reference', connected=True,
                limits=['Documentation of IMD product codes; the codes are encoded in the adapter, not fetched.'],
                action='Keep as the authority for hazard and colour codes.'),
    'S49': dict(status='not_a_source', kind='none', connected=False,
                limits=['Records a context gap: user field, crop and activity information is not a fetched source.'],
                action='Handle as conversation context, not as a source.'),
    'S50': dict(status='not_a_source', kind='none', connected=False,
                limits=['Records an impact gap: terrain, drainage, exposure and vulnerability inputs are not registered.'],
                action='Keep the gap named; no impact model may be implied while it is open.'),
    'S51': dict(status='not_a_source', kind='none', connected=False,
                limits=['Records an evaluation gap: no Gujarati, Hindi or voice acceptance set exists.'],
                action='Keep the gap named; do not claim language acceptance without it.'),
    'S52': dict(status='blocked_access', kind='none', connected=False, via='S58',
                limits=['Registered discovery address returns 401 without credentials.',
                        'Official sea-area text is delivered through the S58/S59 documents.'],
                action='Request an IMD API key; S58 and S59 remain the marine warning supply.'),
    'S53': dict(status='blocked_access', kind='none', connected=False, via='S58',
                limits=['Registered discovery address returns 401 without credentials.',
                        'The same authority serves the sea-area bulletin as a document on the RSMC site.'],
                action='Request an IMD API key; S58 remains the supply.'),
    'S54': dict(status='blocked_access', kind='none', connected=False, via='S59',
                limits=['Registered discovery address returns 401 without credentials.',
                        'The same authority serves the coastal bulletin as a document on the RSMC site.'],
                action='Request an IMD API key; S59 remains the supply.'),
    'S55': dict(status='address_missing', kind='none', connected=False,
                limits=['Index lead only; fishermen warning has no registered address.'],
                action='Discover the fishermen warning route; it overlaps the S58/S59 marine warnings.'),
    'S56': dict(status='active', kind='point', connected=True,
                limits=['Modelled wave fields, never an observed sea state, tide or current.'],
                action='Keep; always name the answering cell and its distance.'),
    'S57': dict(status='active', kind='document', connected=True,
                limits=['Per-district farmer bulletin delivered as a generated PDF; the route is undated, so change detection must measure the body.',
                        'Advice validity is not the same as forecast validity.'],
                action='Keep; extend to the daily document queue and the local-language routes.'),
    'S58': dict(status='reachable_not_connected', kind='document', connected=False,
                limits=['Official sea-area text; the page is reachable and the bulletin sits behind it.',
                        'Never standing in for observed water level, tide or current.'],
                action='Connect as a daily marine document family and name the answering cell distances.'),
    'S59': dict(status='reachable_not_connected', kind='document', connected=False,
                limits=['Official coastal bulletin; the page is reachable.'],
                action='Connect as a daily marine document family alongside S58.'),
    'S60': dict(status='product_address_pending', kind='none', connected=False, via='S62',
                limits=['Station search answers, but the weather payload route is blocked.',
                        'City forecast text is currently delivered through the S62 point route.'],
                action='Re-probe the responsive data route with the exact request the page sends.'),
    'S61': dict(status='active', kind='catalogue', connected=True,
                limits=['Third-party gazetteer; place identity is not administrative truth.'],
                action='Keep for local place resolution.'),
    'S62': dict(status='active', kind='point', connected=True,
                limits=['Best-match model output at a point; not an observation and not an official warning.'],
                action='Keep as the extended forecast supply.'),
    'S63': dict(status='active', kind='layer', connected=True,
                limits=['One host serves many layers; each layer needs its own capture and hash.',
                        'Layer fields are verbatim; meanings are not interpreted.'],
                action='Keep as the geospatial supply; add each newly used layer to the governed capture list.'),
    'S64': dict(status='reachable_not_connected', kind='document', connected=False,
                limits=['The document name is content hashed, so the address changes every issue.',
                        'A printed 20:50 IST issue time is publisher wording, not a verification that the bulletin is current.'],
                action='Discover each issue from the publisher page, verify the printed date, and index the whole document.'),
    'S65': dict(status='reachable_not_connected', kind='document', connected=False,
                limits=['Flash flood guidance is a guidance product for named areas, never an observed water level or a warning level.',
                        'The printed valid-till window is short and must travel with every passage.'],
                action='Ingest both the national and South Asia issues on the daily queue and keep validity attached.'),
    'S66': dict(status='reachable_not_connected', kind='document', connected=False,
                limits=['The set mixes forecast guidance and communication documents; each family is indexed separately.',
                        'Dated filenames use different formats per family, so discovery is by pattern, not by fixed address.'],
                action='Split the set by family and verify the printed date before indexing.'),
    'S67': dict(status='reachable_not_connected', kind='document', connected=False,
                limits=['The sampled issue was dated long before the retrieval date, so the address is stable but the content is event driven.',
                        'A special advisory is never current merely because the file answers.'],
                action='Ingest on the daily queue and refuse to present the advisory as current when the printed date is not the retrieval date.'),
}

DECISIONS = {
    'national_daily_coverage': 'approved_by_user_2026-09-14',
    'pdf_retention': 'seven_days_on_disk_extracted_chunks_retained',
    'source_use': 'approved_local_prototype',
    'redistribution': 'not_approved',
    'scheduling': 'manual_trigger_now_scheduler_later',
}


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def load_registry():
    with open(REGISTRY, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def probe(url, attempts=3):
    """Bounded request with retries. Returns a measurement dict; never raises."""
    last = None
    for attempt in range(attempts):
        last = probe_once(url)
        last['attempts'] = attempt + 1
        if last['http_status'] is not None:
            return last
        if attempt + 1 < attempts:
            time.sleep(1.5 * (attempt + 1))
    return last


def probe_once(url, method='GET', byte_range=None):
    """One bounded request. Returns a measurement dict; never raises on HTTP error."""
    request_id = hashlib.sha256(url.encode('utf-8')).hexdigest()[:12]
    headers = {'User-Agent': UA, 'Accept': '*/*', 'Accept-Language': 'en'}
    if byte_range:
        headers['Range'] = 'bytes=0-%d' % (byte_range - 1)
    request = urllib.request.Request(url, headers=headers, method=method)
    started = time.time()
    result = {'request_id': request_id, 'method': method, 'url': url,
              'checked_at_utc': utcnow(), 'http_status': None, 'content_type': None,
              'content_length': None, 'sample_bytes': 0, 'sample_sha256': None,
              'final_url': url, 'elapsed_ms': None, 'error': None, 'body': None,
              'text': False}
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = response.read(SAMPLE_CAP)
            result['http_status'] = response.status
            result['final_url'] = response.geturl()
            result['content_type'] = (response.headers.get('Content-Type') or '').split(';')[0].strip()
            length = response.headers.get('Content-Length')
            result['content_length'] = int(length) if length and length.isdigit() else None
            result['sample_bytes'] = len(body)
            result['sample_sha256'] = hashlib.sha256(body).hexdigest()
            result['content_range'] = response.headers.get('Content-Range')
            text_types = ('application/json', 'application/geo+json', 'text/csv', 'text/plain',
                          'application/xml', 'text/xml', 'application/vnd.google-earth.kml+xml')
            if result['content_type'] in text_types or body[:5] in (b'<?xml', b'{"sta', b'{"er'):
                result['text'] = True
                result['body'] = body[:SAVE_BODY_CAP].decode('utf-8', 'replace')
    except urllib.error.HTTPError as error:
        result['http_status'] = error.code
        result['content_type'] = (error.headers.get('Content-Type') or '').split(';')[0].strip()
        result['final_url'] = error.geturl() if hasattr(error, 'geturl') else url
        try:
            body = error.read(SAVE_BODY_CAP)
            result['sample_bytes'] = len(body)
            result['sample_sha256'] = hashlib.sha256(body).hexdigest()
            if result['content_type'] in ('application/json', 'text/html', 'text/plain'):
                result['text'] = True
                result['body'] = body.decode('utf-8', 'replace')[:1200]
        except Exception:
            pass
    except Exception as error:  # noqa: BLE001 - the measurement is the point
        result['error'] = '%s: %s' % (type(error).__name__, error)
    result['elapsed_ms'] = int((time.time() - started) * 1000)
    return result


def reconcile(classification, measurement):
    """The probe overrides the curated status where the measurement is decisive."""
    status = classification['status']
    basis = 'curated'
    if measurement is None:
        return status, basis
    code = measurement.get('http_status')
    content_type = measurement.get('content_type') or ''
    if code in (401, 403):
        status, basis = 'blocked_access', 'probe'
    elif code in (404, 410):
        status, basis = 'stale_endpoint', 'probe'
    elif measurement.get('error'):
        status, basis = classification['status'], 'curated_unmeasured'
    elif code and 200 <= code < 300:
        if content_type in ('application/pdf', 'application/zip', 'application/octet-stream'):
            if status != 'active':
                status, basis = 'reachable_not_connected', 'probe'
        elif measurement.get('text') and measurement.get('body'):
            body = measurement['body'].lstrip()
            if body[:1] in ('{', '[') or body.startswith('<?xml'):
                head = body[:200].lower()
                if body[:120].lower().startswith('{"error') or '"error"' in head:
                    status, basis = 'stale_endpoint', 'probe'
                elif status not in ('active', 'not_a_data_product', 'not_a_source'):
                    status, basis = 'reachable_not_connected', 'probe'
    return status, basis


def body_family(measurement):
    if not measurement:
        return None
    content_type = measurement.get('content_type') or ''
    if content_type == 'application/pdf' or (measurement.get('body') or '').startswith('%PDF'):
        return 'pdf'
    if 'html' in content_type:
        return 'html'
    if 'json' in content_type:
        return 'json'
    if 'xml' in content_type or (measurement.get('body') or '').lstrip().startswith('<?xml'):
        return 'xml'
    if 'zip' in content_type:
        return 'zip'
    if 'csv' in content_type:
        return 'csv'
    return content_type or None


def connector_of(source_id, classification):
    """Two separate facts, kept separate.

    `ingested` says a registered connector pulls this source into the local corpus.
    `wired_to_chat` says an ordinary conversation can reach it. A source can be the
    first without being the second, and reporting one as the other would overstate
    what a user can actually ask for.
    """
    families = sorted(INGESTED_BY_FAMILY.get(source_id, []))
    ingested = bool(families) or classification['connected']
    wired = ingested and (classification['connected'] or source_id in CORPUS_SOURCES)
    return {'kind': classification['kind'],
            'kind_meaning': KIND_MEANINGS[classification['kind']],
            'connected': ingested,
            'ingested_by_families': families,
            'wired_to_chat': wired,
            'reachability_note': (None if wired or not families else
                                  'A registered document family ingests this source into the local corpus. '
                                  'It is not yet reachable from a conversation.')}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--offline', action='store_true', help='do not probe; reuse the last measurement')
    parser.add_argument('--only', default=None, help='comma-separated source ids to probe')
    parser.add_argument('--apply', action='store_true', help='stamp sources.json review fields from the ledger')
    args = parser.parse_args()

    registry = load_registry()
    products = {p['id']: p for p in registry['products']}
    wanted = set(args.only.split(',')) if args.only else None
    mismatch = sorted(set(C) ^ set(products))
    if mismatch:
        print('classification/registry mismatch: %s' % ', '.join(mismatch))
        return 2

    previous = {}
    reused = None
    if os.path.exists(LEDGER):
        with open(LEDGER, 'r', encoding='utf-8') as handle:
            old = json.load(handle)
        previous = {row['id']: row.get('probe') for row in old.get('sources', [])}
        if args.offline and old.get('evidence_directory'):
            reused = old['evidence_directory']

    # An offline rebuild reuses the recorded probes, so it must not overwrite the frozen
    # evidence directory those probes were measured into. It writes its own manifest and
    # the ledger keeps pointing at the measurement run.
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    evidence_dir = os.path.join(EVIDENCE_ROOT, 'source-audit-' + stamp)
    os.makedirs(evidence_dir, exist_ok=True)
    manifest = {'generated_at_utc': utcnow(), 'user_agent': UA, 'sample_cap_bytes': SAMPLE_CAP,
                'probes': [], 'offline': args.offline, 'reused_measurements_from': reused}

    rows = []
    counts = {}
    for source_id in sorted(products):
        product = products[source_id]
        classification = C[source_id]
        url = product.get('access_url')
        measured = None
        if url and not args.offline and (wanted is None or source_id in wanted):
            measured = probe(url)
        carried = False
        if measured is None and url and previous.get(source_id):
            measured = dict(previous[source_id])
            measured.pop('body', None)
            carried = True
        if url is None:
            status, basis = classification['status'], 'curated'
        elif measured is None:
            status, basis = 'unmeasured', 'none'
        else:
            status, basis = reconcile(classification, measured)
        row = {
            'id': source_id,
            'product': product.get('product'),
            'category': product.get('category'),
            'registry_evidence_stage': product.get('evidence_stage'),
            'access_url': url,
            'status': status,
            'status_meaning': STATUS_MEANINGS.get(status),
            'status_basis': basis,
            'curated_status': classification['status'],
            'payload_family': body_family(measured),
            'via': classification.get('via'),
            'connector': connector_of(source_id, classification),
            'probe': measured,
            'carried_from_previous': carried,
            'limits': classification.get('limits', []),
            'next_action': classification.get('action'),
        }
        rows.append(row)
        counts[status] = counts.get(status, 0) + 1
        if measured and not carried:
            if not args.offline:
                manifest['probes'].append({k: v for k, v in measured.items() if k != 'body'})
            if measured.get('body'):
                name = '%s-%s.response' % (source_id, measured['request_id'])
                with open(os.path.join(evidence_dir, name), 'w', encoding='utf-8') as handle:
                    handle.write(measured['body'])
        code = (measured or {}).get('http_status')
        print('%-4s %-24s %-22s %-8s %s' % (source_id, status,
                                             (measured or {}).get('content_type') or '-',
                                             code if code else ('carried' if carried else '-'),
                                             ((measured or {}).get('error') or '')[:60]))

    with open(os.path.join(evidence_dir, 'manifest.json'), 'w', encoding='utf-8') as handle:
        json.dump(manifest, handle, indent=1, sort_keys=True)

    ledger = {
        'schema_version': SCHEMA_VERSION,
        'compiled_at_utc': utcnow(),
        'title': 'Source activation review',
        'scope': 'Every source registered in data/registry/sources.json, measured at its registered address.',
        'policy': {
            'review_decision': 'approved_local_prototype',
            'redistribution': 'not_approved',
            'production_approval': 'not_granted',
            'note': ('Registration is not selection and a reachable address is not a validated product. '
                     'Approval covers local prototype use of technically verified addresses only; it grants '
                     'no redistribution right and no operational clearance.'),
            'decisions': DECISIONS,
        },
        'status_vocabulary': STATUS_MEANINGS,
        'connector_kinds': KIND_MEANINGS,
        'counts': counts,
        'probe_failures': sorted(row['id'] for row in rows if (row['probe'] or {}).get('error')),
        'evidence_directory': reused or os.path.relpath(evidence_dir, ROOT),
        'rebuild_evidence': os.path.relpath(evidence_dir, ROOT) if reused else None,
        'sources': rows,
    }
    with open(LEDGER, 'w', encoding='utf-8') as handle:
        json.dump(ledger, handle, indent=1, sort_keys=False)
        handle.write(chr(10))

    print('')
    print(json.dumps(counts, indent=1))
    print('ledger: %s' % os.path.relpath(LEDGER, ROOT))
    print('evidence: %s' % os.path.relpath(evidence_dir, ROOT))

    if args.apply:
        stamp_registry(registry, rows)
    return 0


def stamp_registry(registry, rows):
    by_id = {row['id']: row for row in rows}
    for product in registry['products']:
        row = by_id[product['id']]
        product['user_review'] = 'approved_local_prototype'
        product['review_ledger'] = 'data/registry/source-review.json'
        product['ledger_status'] = row['status']
        product['ledger_checked_at_utc'] = (row['probe'] or {}).get('checked_at_utc')
    version = registry.get('registry_version', 0) + 1
    registry['registry_version'] = version
    registry['updated_at_utc'] = utcnow()
    registry['review_policy'] = ('Source registration and operational selection are distinct. The user approved '
                                 'local prototype use of technically verified addresses on 2026-09-14; '
                                 'redistribution is not approved and no production source is selected.')
    registry.setdefault('change_history', []).append({
        'registry_version': version,
        'recorded_at_utc': utcnow(),
        'change': ('Record the source activation review: every registered address measured, statuses and '
                   'connectors recorded, and local prototype use approved. No source becomes production-ready '
                   'and no redistribution right is granted.'),
        'evidence_date': datetime.now(timezone.utc).date().isoformat(),
        'report': 'docs/29-source-activation-ledger.md',
        'ledger': 'data/registry/source-review.json',
    })
    with open(REGISTRY, 'w', encoding='utf-8') as handle:
        json.dump(registry, handle, indent=2, ensure_ascii=False)
        handle.write(chr(10))
    print('stamped %d registry entries at version %d' % (len(registry['products']), version))


if __name__ == '__main__':
    sys.exit(main())
