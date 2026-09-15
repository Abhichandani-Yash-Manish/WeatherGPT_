import pathlib
NL = chr(10)
m = pathlib.Path('weathergpt_data/briefing_run.py')
t = m.read_text()
anchor = 'FORECAST_PARAMETERS = ('
assert t.count(anchor) == 1
note = ("RUNNER_NOTE = ('This is a foreground run of a local prototype. Nothing is delivered, pushed or scheduled outside this '" + NL
        "               'process; a briefing records what the connected products published at the instant it ran.')" + NL + NL)
t = t.replace(anchor, note + anchor, 1)
m.write_text(t)

s = pathlib.Path('scripts/briefing.py')
st = s.read_text()
old_import = 'from weathergpt_data.briefing_run import compose, load_previous, markdown, resolve_place, summary_line  # noqa: E402'
assert st.count(old_import) == 1
st = st.replace(old_import, 'from weathergpt_data.briefing_run import (RUNNER_NOTE, compose, load_previous, markdown,  # noqa: E402' + NL + '                                           resolve_place, summary_line)', 1)
old_local = ("RUNNER_NOTE = ('This is a foreground run of a local prototype. Nothing is delivered, pushed or scheduled outside this process; '" + NL
             "               'a briefing records what the connected products published at the instant it ran.')")
assert st.count(old_local) == 1, st.count(old_local)
st = st.replace(old_local, '', 1)
s.write_text(st)
print('patched')