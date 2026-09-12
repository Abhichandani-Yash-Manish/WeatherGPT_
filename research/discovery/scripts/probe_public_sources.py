"""Bounded, unauthenticated discovery probes. These are not production connectors.

Run from any directory with Python 3. Each run preserves its own response snapshots.
No login, account creation, or endpoint guessing is performed.
"""
import concurrent.futures
import datetime as dt
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {
    "imd-city-mapping": "https://api.imd.gov.in/api/v1/cityforecast_mapping",
    "imd-current": "https://api.imd.gov.in/api/v1/current_wx",
    "imd-city-forecast": "https://api.imd.gov.in/api/v1/cityforecast",
    "imd-nowcast": "https://api.imd.gov.in/api/v1/districtnowcast",
    "imd-warning": "https://api.imd.gov.in/api/v1/districtwarning",
    "imd-cap-rss": "https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml",
    "imd-ahmedabad": "https://mausam.imd.gov.in/ahmedabad/",
    "imd-agromet-crop": "https://imdagrimet.gov.in/cropAdvisory_3.php",
}
MAX_BYTES = 1_000_000


def probe(name, url, output):
    result = {"id": name, "url": url, "authentication": "none",
              "checked_at_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
    request = urllib.request.Request(url, headers={"User-Agent": "WeatherGPT-source-discovery/0.1"})
    try:
        try:
            response = urllib.request.urlopen(request, timeout=20)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            body = response.read(MAX_BYTES + 1)
            result.update(http_status=response.code, final_url=response.url,
                          content_type=response.headers.get("Content-Type"),
                          truncated=len(body) > MAX_BYTES)
            body = body[:MAX_BYTES]
            destination = output / (name + ".response")
            destination.write_bytes(body)
            result.update(bytes_saved=len(body), sha256=hashlib.sha256(body).hexdigest(),
                          snapshot=str(destination.relative_to(ROOT)))
    except Exception as exc:
        result.update(error_type=type(exc).__name__, error=str(exc))
    return result


def main():
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = ROOT / "evidence" / stamp
    output.mkdir(parents=True, exist_ok=False)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(probe, name, url, output) for name, url in TARGETS.items()]
        results = [future.result() for future in futures]
    manifest = {"scope": "Single requests; availability and content only, no reliability/SLA claim",
                "sample_geography": "National endpoints; Ahmedabad regional page. No district ID assumed.",
                "results": results}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({"manifest": str(output / "manifest.json"), "results": results}, indent=2))


if __name__ == "__main__":
    main()
