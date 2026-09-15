set -e
cd /Users/yashabhichandani/Desktop/WeatherGPT
export HOME=/Users/yashabhichandani
cat > /tmp/round17.md <<'EOF'
## Round 17 — the chat surface, and the key you paste

A read-only audit of fourteen live chat journeys ran against this workspace. It found the engine alive (11/14
answered cleanly, none errored, honest partials), and it found the gap the user named: capability the page did
not show.

| Found | Repaired |
|---|---|
| `table is not defined`: an answer carrying retrieval coverage failed to render **the whole turn** | Shared table builder; an offline render check now pins it |
| "waves off Kochi" asked which place, listing four inland Maharashtra hamlets first | Tied candidates are decided by the connected product (a wave cell exists only near the coast) and disclosed; a ranked preference still wins first |
| The right-now reading led with a five-month-old AWS row 29 km away | Fresh stations (≤3 h) lead; the nearest is named only when it is not the freshest; a >3 h floor says so |
| "right now in Kochi" resolved to a Maharashtra village | Tied candidates are scored by distance to the nearest *fresh* station; Kerala wins, alternatives named |
| English 'morning' 09:30–12:30 vs Hindi 'सुबह' 06:30–12:30; Gujarati 'સવારે' matched nothing (`\b` fails on combining marks) | One part-of-day definition across scripts, with boundary matching that survives vowel signs |

Wired into the conversation: **Right now here**, **Write the alert brief**, **Write the advisory brief** (carrying
the edition the turn read) and **Write a briefing**, each with save-to-briefcase where a brief exists, plus a
**What was retrieved, and what is missing** block (pending slots, coverage counts, edition comparison, printed
issue dates and currency in words). The trace now names the provider, model, model calls and failover.

Providers: `python3 scripts/models.py --set-key` writes the key at mode 0600 without echoing it; paid ids are
refused with a reason; twelve free models are ranked most capable first; OpenRouter is tried before the local
model and a refusal is recorded as failover — measured with an invalid key (HTTP 401 → local model answered).
A valid-key call still needs your key.

EOF
cat /tmp/round17.md >> docs/49-engine-architecture-and-gap-analysis.md
grep -c 'Round 17' docs/49-engine-architecture-and-gap-analysis.md
