set -e
cd /Users/yashabhichandani/Desktop/WeatherGPT
cat > /tmp/round8.md <<'EOF'
## Round 8 — WS8: the language and voice path re-measured, and two gate defects repaired

The language path had not been re-measured since the engine work. Re-measuring it found two real
defects, both of which shipped a rendering that should not have been shown.

| Found and repaired | Where |
|---|---|
| A Tamil rendering carrying **Telugu characters** passed the script check; `written_in` only counted the target script | weathergpt_data/languages.py (`foreign_script_letters`), weathergpt_data/rendering.py |
| The gate computed a script verdict and **never used it**, so prose not written in the requested language could still report ok | weathergpt_data/rendering.py |
| A refused script rendering was reported to the reader as an **unreachable translation service** | weathergpt_data/answer_language.py (`rendered_in_another_script`) |
| An explicit **agromet advisory with a crop** read the district warning product, because "advisory" is also a warning word | weathergpt_data/rule_planner.py (a crop with advisory wording and no warning word is the agriculture shape) |
| "Ahmedabad, Gujarat mein …" was planned as **Gujarat**, and twenty villages called Gujar were offered | weathergpt_data/rule_planner.py (the comma pair keeps its qualifier as the state) |
| A midnight-to-midnight day was explained as "read as 00:30 to 00:30 IST", naming no date | weathergpt_data/transport.py |

### The ledger, re-measured under the stricter gate

- Write: **19 of 23** verified. Tamil, Sindhi, Santali and Manipuri fail, each with its own reason
  recorded in data/registry/language-support.json.
- Speak and hear: **10 of 23** each (English, Hindi, Bengali, Gujarati, Kannada, Malayalam, Marathi,
  Odia, Punjabi, Telugu). A stricter gate lowering a count is the ledger working, not a regression hidden.

### Journeys and audio

- Six recorded turns: three honest downgrades (`values_did_not_survive`), one Gujarati template answer,
  one verified rendering with protected values, one refusal named `rendered_in_another_script`, and a
  Hindi clarification rendered through the gate with all twenty candidates kept as published.
- Real audio for Hindi and Gujarati: the Hindi number came back as a word rather than digits, the
  Gujarati unit marker did not come back, and recognition probability was absent for one probe and is
  recorded as unknown rather than invented.
- Document coverage is now a number: 107 of 6,739 indexed passages carry Devanagari, all of them
  bilingual letterheads, so coverage in the language sense is not established and is not claimed.

### What this does not establish

- No fluency, accuracy or native acceptability; no native speaker has reviewed any output.
- No mobile, noisy-input, barge-in, screen-reader or cross-browser voice acceptance.
- WS8 is not finished: document coverage in the language sense remains open, and the voice path is
  measured on the service's own audio, not on a noisy field recording.

EOF
cat /tmp/round8.md >> docs/49-engine-architecture-and-gap-analysis.md
grep -c 'Round 8' docs/49-engine-architecture-and-gap-analysis.md
