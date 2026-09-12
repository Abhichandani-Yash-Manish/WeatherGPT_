# WeatherGPT question-to-evidence map

Working geography: Ahmedabad district, Gujarat. Discovery remains national. All audiences have equal importance; farmer workflows lead the demonstration. These are proposed acceptance cases, not claims of implemented behavior or validated user demand.

| ID | Audience and question | Evidence needed | Discovery acceptance condition |
|---|---|---|---|
| Q01 | Citizen: What is the weather here now? | Observation, station identity/coordinates, timestamp, units, quality flags | Can distinguish a measurement at a station from conditions at the user's position |
| Q02 | Citizen: What is tomorrow afternoon's forecast? | Subdaily forecast, requested interval, source/model and location | Source genuinely resolves the requested hours; daily maxima alone fail this case |
| Q03 | All: Is there an official warning for my village? | Current alert, area, validity, authoritative village/district mapping | Geographic and temporal applicability established without assuming city equals district |
| Q04 | Farmer: What does the current advisory say for my crop? | District/AMFU bulletin, crop and stage, issue/revision information | Passage retains its district, crop, stage, conditions and page citation |
| Q05 | Farmer: How does weather affect my planned field operation? | Forecast, official warning, applicable guidance, user-supplied activity and field context | Clearly identifies missing inputs and avoids unsupported operation thresholds |
| Q06 | Farmer: Has advice relevant to my plan changed? | Versioned advisories and forecasts, saved plan, re-evaluation rule | Earlier and later evidence can be compared for the same activity and time window |
| Q07 | Citizen: Has the forecast for my outdoor plan changed? | Comparable archived forecast runs and user constraints | Distinguishes a new prediction from a change in provider, grid or units |
| Q08 | Disaster operator: Which areas fall within this warning? | Warning geometry/codes, versioned boundaries | Areas can be matched deterministically; missing geometry is explicit |
| Q09 | Disaster operator: Was this warning updated or cancelled? | Alert identifiers, references, message type, validity history | Correct lifecycle can be reconstructed; feed absence is not interpreted as cancellation |
| Q10 | Researcher: Compare this monsoon with a reference period | Historical rainfall, declared baseline/season and spatial aggregation | Files expose sufficient coverage and missingness for a reproducible calculation |
| Q11 | Researcher: How long was the dry spell? | Daily rainfall, threshold, missingness rule | Missing observations cannot silently count as zero rainfall |
| Q12 | Researcher: Which forecast performed better here? | Archived pre-event predictions, compatible observations, run and valid times | No future evidence enters a historical forecast comparison |
| Q13 | Researcher: Export the data behind that chart | Permitted data subset, provenance, method and version | Export and computation can be reproduced and redistribution conditions are known |
| Q14 | All: Explain a warning in Gujarati and English | Authoritative explanation, local terminology, language variants | Location, time, severity and negation retain their meaning across languages |
| Q15 | Farmer: Ask a weather question by voice using local place names | Representative test utterances, place-name aliases, transcription/voice capability | Capture the intended place, date and activity; transcription uncertainty can be clarified |
| Q16 | All: What can you tell me while a source is unavailable? | Last successful retrieval, record validity, coverage and fallback policy | Stale/unavailable state is distinct from no warning or zero rainfall |
| Q17 | All: Why do two sources disagree? | Comparable product definitions, upstream lineage, intervals and resolutions | Comparison explains relevant differences without inventing a confidence probability |
| Q18 | All: Show the NWP forecast behind the answer | Identifiable NWP product, run/lead time, grid, variable and units | Provider branding alone does not establish model identity |
| Q19 | Researcher: Does radar or satellite evidence help answer this question? | Named product, observation time, projection, calibration and quality information | A concrete analytical use is identified before ingesting a large imagery archive |
| Q20 | Disaster operator: What additional evidence is needed for flood impact? | Hydrological information plus suitable exposure/vulnerability inputs and method | Rainfall forecasts remain distinct from validated flood-impact predictions |

| Q21 | Aviation user: Show a sourced briefing for a selected airport and time | Airport identity, METAR observation, TAF issue/validity and amendments; applicable official advisories | Decode weather with provenance and explicit missing briefing components; never infer flight clearance from a land model |
| Q22 | Marine user: What forecast and official bulletin apply to this coastal or sea area? | Named coastal/sea region, bulletin issue/validity, wave-model grid/time/units and relevant warnings | Establish region and time applicability; distinguish modeled waves from official warnings and never infer navigation safety |

PS coverage: real-time retrieval Q01/Q16; natural-language forecasts Q02/Q07/Q17; NWP Q12/Q18; extreme alerts Q03/Q08/Q09; location advisories Q04/Q05/Q06; multilingual Q14; climate/history Q10/Q11/Q13; voice Q15. Q19/Q20 capture further data discovery relevant to the stated background and decision-support ambition. Aviation and marine use cases are explicitly covered by Q21/Q22. No specialist capability is considered operational merely because its source appears in the register.

Start by collecting representative samples for Q01-Q05, Q08-Q09 and Q10. The remaining cases guide gaps and further discovery. Case sequence does not reduce audience importance or final feature coverage.
