# First working data component: national historical climate

The S25 rainfall and S26 mean-temperature snapshots now support a reproducible local build and structured lookup. Python 3.10+ and its standard library are sufficient; no API key, server, LLM or package installation is required.

Run from the WeatherGPT project directory:

```sh
python3 -m weathergpt_data build-climate
```

The command prints its output directory under `data/processed/climate/`. The directory identity depends on the source hashes and implementation hash. The current completed build is [national-climate-v1-a203fc0eb4a31c58](../data/processed/climate/national-climate-v1-a203fc0eb4a31c58).

```sh
python3 -m weathergpt_data lookup-climate \
  --database data/processed/climate/national-climate-v1-a203fc0eb4a31c58/climate.sqlite \
  --source S25 --year 2024 --period ANNUAL
```

This returns the published value, unit, quality flags, original CSV location and a separate reconciliation record. S25 is rainfall; S26 is mean temperature. Supported periods are `ANNUAL`, `M01`–`M12`, `JF`, `MAM`, `JJAS` and `OND`. Only the supplied **All India aggregate, 1901–2024** is supported. District requests, uncovered years and unsupported periods fail explicitly. The command is a structured data query; conversational query interpretation is not implemented yet.

## Outputs

| File | Content |
|---|---|
| `records.csv` / `records.jsonl` | 4,216 records with explicit period and source provenance. |
| `climate.sqlite` | Queryable records and rainfall reconciliations. Values use decimal strings to retain the source representation without binary floating-point rounding. |
| `reconciliation.json` | Published rainfall totals, month sums, differences and documented rounding bounds. |
| `audit.json` | Counts, exact source-cell checks and discrepancies. |
| `build-manifest.json` | Input, implementation and output hashes; build timestamp is distinct from source retrieval time. |
| `example-answer.md` / `.json` | One human-readable answer and its inspectable evidence. |

Published aggregate rows overlap with months, so do not sum across period types. Temperature aggregates are retained without attempting to reproduce them by an unweighted monthly mean. Missing rainfall stays missing. The parser rejects changed schemas, inconsistent units/geography/source identity, duplicates, non-finite values and negative rainfall. The frozen snapshot build rejects unexpected year coverage rather than silently assuming a changed file is compatible.

Source bytes are checked against the registry's asset manifest. A repeated build returns the same directory only after checking its output hashes. Existing outputs are not overwritten. Changed input or implementation requires a distinct build; new source evidence must first be registered intentionally. No current weather is retrieved during this build.

## Verification and next integration

```sh
python3 -m unittest discover -s tests -v
python3 data/registry/scripts/manage_registry.py --check
```

The [implementation](../weathergpt_data/climate.py), [tests](../tests/test_climate.py), and [executed notebook](../research/discovery/processing-checkpoint.ipynb) are inspectable. The next application adapter should call `lookup()` with validated structured arguments and surface its citation and flags. Any baseline/trend computation needs a separate explicit period, completeness rule and scientific method; the current lookup does not establish climate attribution or local forecast skill.
