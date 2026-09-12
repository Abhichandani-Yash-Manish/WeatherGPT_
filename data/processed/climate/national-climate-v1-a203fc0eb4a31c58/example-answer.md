# First reproducible WeatherGPT answer

**Question:** What was India's annual rainfall in 2024?

The supplied IMD All India table reports **1206.6 mm** for 2024. This is a national historical aggregate.

Its twelve published months sum to **1204.1 mm**, a difference of **2.5 mm** from the published annual total. The pipeline preserves the published total and flags the discrepancy; it does not silently repair it.

Source: [IMD rainfall table](https://dsp.imdpune.gov.in/home_ogd_rainfall.php), S25, CSV row 125, column `Annual`. See `example-answer.json` for the exact source path and hash.
