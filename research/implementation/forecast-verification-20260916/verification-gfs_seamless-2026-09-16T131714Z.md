# Forecast verification — 23.0258, 72.5873

Model: **gfs_seamless** · forecast source: S70 · reference: S22 ERA5 hourly reanalysis
Window: 2026-08-28 to 2026-09-10 (UTC) · grid: {"latitude": 23.019852, "longitude": 72.53906}
Retrieved (UTC): 2026-09-16T13:17:03.199790+00:00 (forecast), 2026-09-16T13:17:03.827673+00:00 (reference)

Every figure describes the matched sample for this model, variable and window. It is not operational skill, a confidence or a risk, and no model is ranked against another.

## precipitation
| Lead (days) | Matched hours | Bias | MAE | RMSE | Correlation |
|---|---|---|---|---|---|
| 1 | 336 | -0.008 | 0.016 | 0.062 | -0.026 |
| 2 | 336 | -0.011 | 0.013 | 0.039 | -0.036 |
| 3 | 336 | 0.008 | 0.031 | 0.138 | 0.042 |
| 5 | 336 | -0.010 | 0.013 | 0.040 | 0.010 |
| 7 | 336 | -0.009 | 0.015 | 0.043 | -0.052 |

## temperature_2m
| Lead (days) | Matched hours | Bias | MAE | RMSE | Correlation |
|---|---|---|---|---|---|
| 1 | 336 | 1.596 | 1.707 | 2.055 | 0.923 |
| 2 | 336 | 1.553 | 1.642 | 1.969 | 0.920 |
| 3 | 336 | 1.294 | 1.700 | 2.100 | 0.810 |
| 5 | 336 | 0.918 | 1.224 | 1.496 | 0.867 |
| 7 | 336 | 1.017 | 1.197 | 1.454 | 0.906 |

## Limits
- The reference is ERA5 reanalysis, a modelled analysis, not a station observation.
- The statistics describe this sample for this model, variable and window; they are not operational skill, a confidence or a risk.
- A lead with fewer than 24 matched hours is reported as unmeasured, not given a number.
- A model is never ranked against another and no single skill score is produced.
