import pathlib
p = pathlib.Path('web/panels.js')
t = p.read_text()
start = t.index("  WG.advisoryBriefDrawer = function (WGref, params) {")
end = t.index("  WG.nowDrawer = function (WGref, place) {")
block = t[start:end]
old = "        body.append(el('p', brief.status_line || brief.why || 'No brief was composed.', 'block-note'));"
assert block.count(old) == 1, 'header anchor inside the advisory drawer'
new = ("        const region = String(((brief.published_advice || {}).region) || request.region);" + chr(10) +
       "        body.append(el('p', brief.status === 'ok'" + chr(10) +
       "          ? ('Published advice for ' + region + ' quoted below, with the model forecast kept apart as context.')" + chr(10) +
       "          : String(brief.why || brief.status_line || 'No brief was composed.'), 'block-note'));" + chr(10) +
       "        if (brief.forecast_status) body.append(el('p', 'Forecast context: ' + String(brief.forecast_status), 'field-note'));" + chr(10) +
       "        if ((brief.conditions_named_by_the_source || []).length) {" + chr(10) +
       "          const conditions = el('ul', undefined, 'notes');" + chr(10) +
       "          (brief.conditions_named_by_the_source || []).forEach(item => conditions.append(el('li', String(item))));" + chr(10) +
       "          body.append(el('p', 'Conditions the source itself names', 'field-label'));" + chr(10) +
       "          body.append(conditions);" + chr(10) +
       "        }")
block = block.replace(old, new, 1)
t = t[:start] + block + t[end:]
p.write_text(t)
print('advisory drawer header fixed')