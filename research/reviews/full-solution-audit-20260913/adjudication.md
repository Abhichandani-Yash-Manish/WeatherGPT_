# Fresh probe adjudication

22 local HTTP turns: 16 initial challenge turns, four diagnostic follow-ups, two straightforward supported controls. These were authored for this review, not sampled from a population. No overall success percentage is inferred. Application status is recorded separately from the reviewer's assessment. No code was repaired between these probes. The full JSON packets preserve plans, task results, citations, timings and model traces.

| Packet in `live-probe/` | App status | Review assessment |
|---|---|---|
| forecast_continuity-1.json | partial | Requested Kochi variables retrieved; UTC-aligned source intervals do not cover the entire explicit 09:00–12:00 IST request. Useful partial evidence, not full-window completion. |
| forecast_continuity-2.json | partial | Place/date/parameters retained when time changed. Same boundary limitation at 15:00–18:00. |
| forecast_continuity-3.json | partial | Failed explicit change to rain amount: retained probability/gusts/feels-like. This is an interpretation/context defect in addition to source-window limits. |
| official_warning-1.json | unavailable | Honest Chennai warning-source limitation. Applicable current warning requirement remains unfulfilled; this is not evidence of no warnings. |
| dissemination-1.json | unavailable | Patna notification request reduced to a one-time diagnostic. Delivery action and its unsupported state were not explicitly resolved. No fabricated subscription confirmation. |
| observation-1.json | unavailable | General Mysuru live station observation unavailable. Correctly did not substitute a forecast. |
| agriculture-1.json | needs_clarification | Indore bulletin failed issue-date extraction; district-wide forecast correctly requested a town. Two different gaps preserved, no useful advisory retrieved. |
| aviation-1.json | partial | METAR facts retrieved; current usable TAF held. Separate explanation falsely says no current weather data was supplied. Not a complete evidence-based briefing. |
| marine-1.json | unavailable | Marine chat/sea identity absent. Correctly did not substitute land weather. |
| river-1.json | unavailable | No requested observed gauge level/danger comparison. Discharge adapter existence cannot fulfill it. |
| history-1.json | unavailable | Mysuru source-name lookup failed; diagnostic alias probe below distinguishes alias failure from historical year coverage. |
| climate-1.json | answered | Forty values, trend and methodological notes retrieved; explicit explanation task is only a generic label. Numeric operation works; complete-task label is too generous. No independent climate-skill claim. |
| hindi-1.json | needs_selection | Source-backed Bhopal ambiguity presented in Hindi. An appropriate intermediate choice, not a completed probability answer. |
| gujarati-1.json | answered | Probability data retrieved, but explicit Gujarati output requirement failed: answer is English. |
| district_scope-1.json | needs_clarification | Correctly refuses to treat a point as Wayanad district average. The requested area statistic remains unsupported; selecting a town would change the scope. |
| multi_task-1.json | partial | All four Bhubaneswar tasks preserved. Forecast evidence returned; official warning and general observation missing; historical district identity unresolved. Task accounting improvement, limited information completion. |
| rain_correction.json | partial | Stronger explicit instruction finally switches to precipitation; exact comparison window remains partial. Does not erase the earlier ordinary-language failure. |
| language_correction.json | answered | Explicit Gujarati correction still returns English. Repeated language failure. |
| hindi_selection.json | needs_selection | Natural reply naming Bhopal city in Bhopal district repeats earlier ambiguity. Text clarification failed; UI selection was not tested here. |
| historical_alias.json | partial | Source name Mysore unlocks 2010; 2020 correctly withheld because stored series ends in 2010. Alias and time coverage are distinct limitations. |
| supported_forecast.json | answered | Straightforward aligned-window Kochi rain-amount request produces a concise GFS answer with supporting packet evidence. Successful scoped control. |
| supported_history.json | answered | Straightforward published All India annual-rainfall lookup returns the requested value and citation evidence. Successful scoped control. |

The five app-labelled answered packets include two supported controls, two English responses to Gujarati requirements, and the incomplete trend explanation. They cannot be used as an acceptance numerator. Conversely, the intentionally unsupported/ambiguous questions cannot be used to estimate general failure frequency. None of the 22 turns had a transport/uncaught exception; that is not proof of semantic correctness or sustained reliability.

New numerical packets were inspected for task/response behavior rather than exhaustively replayed from source bytes. Previous source-byte verification remains recorded in the implementation evidence. This review makes no new claim that every source value or forecast is scientifically correct.
