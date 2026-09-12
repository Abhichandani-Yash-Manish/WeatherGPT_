"""Audit the saved September 11 discovery samples, without network requests.

Run with Python 3. Source dates are fixed intentionally: this checks evidence,
not current conditions. A passing audit does not establish forecast accuracy.
"""
import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "evidence"
FOLDERS = [
    "broad-20260911T160113Z", "numeric-20260911T160221Z",
    "imd-live-20260911T160337Z", "imd-grid-20260911T160416Z",
    "imd-context-20260911T160450Z",
]


def read(folder, name):
    return json.loads((E / folder / (name + ".response")).read_text())


def main():
    requests = []
    for folder in FOLDERS:
        for record in json.loads((E / folder / "manifest.json").read_text())["results"]:
            if record.get("snapshot"):
                data = (ROOT / record["snapshot"]).read_bytes()
                assert len(data) == record["bytes_saved"], record["id"]
                assert hashlib.sha256(data).hexdigest() == record["sha256"], record["id"]
                assert not record["truncated"], record["id"]
            requests.append(record)

    forecast = read(FOLDERS[3], "imd-mausamgram-grid")
    assert len(forecast) == 15
    assert all(len(v) == 41 and v[0] == "NaN" for v in forecast.values())
    assert all(isinstance(x, (int, float)) for v in forecast.values() for x in v[1:])
    bc = read(FOLDERS[4], "imd-temperature-bc")
    assert bc["fcsthours"] == list(range(0, 121, 3))
    assert all(len(bc[k]) == 41 for k in ["temp_bc_realtime", "fcsttemp", "fcsttemp_bc_p5days"])
    warn = read(FOLDERS[2], "imd-ahmedabad-warning")["features"]
    assert len(warn) == 1 and warn[0]["properties"]["District"] == "AHMADABAD"
    assert warn[0]["properties"]["Obj_id"] == 273
    assert warn[0]["geometry"]["type"] == "MultiPolygon"
    station = read(FOLDERS[0], "awc-station")[0]
    assert station["icaoId"] == "VAAH" and station["wmoId"] == "42647"
    metars = read(FOLDERS[0], "awc-metar")
    assert len(metars) == 5 and all(x["icaoId"] == "VAAH" for x in metars)
    taf = read(FOLDERS[0], "awc-taf")
    assert len(taf) == 1 and taf[0]["validTimeTo"] > taf[0]["validTimeFrom"]
    gfs = read(FOLDERS[1], "openmeteo-gfs")
    assert all(len(v) == 72 for v in gfs["hourly"].values())
    assert gfs["utc_offset_seconds"] == 19800
    era = read(FOLDERS[1], "openmeteo-era5")
    assert all(len(v) == 7 for v in era["daily"].values())
    power = read(FOLDERS[1], "nasa-power-daily")
    assert power["header"]["time_standard"] == "UTC"
    assert all(len(v) == 7 for v in power["properties"]["parameter"].values())
    report = {
        "scope": "Offline structural and integrity audit of bounded saved samples",
        "audited_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "outcome": "passed",
        "request_count": len(requests),
        "http_200_count": sum(r.get("http_status") == 200 for r in requests),
        "warning": "HTTP 200 counts include pages, code and a no-data response; not a count of usable weather APIs",
        "sample_results": {
            "imd_mausamgram": {"arrays": 15, "entries_each": 41, "initial_missing_marker": "NaN", "grid": [23.0, 72.5], "cycle": "2026091100"},
            "imd_warning": {"district": "AHMADABAD", "object_id": 273, "issue_date": warn[0]["properties"]["Date"], "geometry_checked": "type only; validity and containment not tested"},
            "awc": {"station": "VAAH", "wmo_id": "42647", "metar_count": 5, "taf_count": 1},
            "gfs_via_openmeteo": {"hourly_count": 72, "variables": list(gfs["hourly_units"]), "returned_grid": [gfs["latitude"], gfs["longitude"]]},
            "era5_via_openmeteo": {"daily_count": 7, "time_basis": "Asia/Kolkata"},
            "power": {"daily_count": 7, "time_basis": "UTC", "sources": power["header"]["sources"]},
        },
        "requests": requests,
        "not_established": ["Forecast skill", "Production reliability", "Supported IMD public-site API contract", "District/village representativeness", "User usefulness"],
    }
    destination = ROOT / "broad-sample-audit.json"
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Audit passed for {len(requests)} recorded requests. Wrote {destination}")


if __name__ == "__main__":
    main()
