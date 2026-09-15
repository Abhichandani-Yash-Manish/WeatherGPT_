import pathlib
p = pathlib.Path('web/views.js')
t = p.read_text()
snippet = pathlib.Path('tmp/views-actions-snippet.js').read_text()
anchor = 'function renderActions(packet, handlers) {'
assert t.count(anchor) == 1, t.count(anchor)
t = t.replace(anchor, snippet + chr(10) + anchor, 1)
old = "  if (handlers.onDownload) actions.append(actionButton('Download this answer as JSON', () => handlers.onDownload(packet)));"
assert t.count(old) == 1, t.count(old)
added = (old + chr(10) + "  /* The artefacts this reader can ask for next, where the answer makes them reachable. */" + chr(10) +
         "  const WGx = window.WG || {};" + chr(10) +
         "  const drawers = WGx.briefDrawers;" + chr(10) +
         "  if (drawers) {" + chr(10) +
         "    const place = resolvedPlace(packet);" + chr(10) +
         "    if (place) {" + chr(10) +
         "      actions.append(actionButton('Right now here', () => drawers.now(WGx, place)));" + chr(10) +
         "      const warningTurn = ((packet.plan || {}).intent === 'warning') || warningFacts(packet).length > 0;" + chr(10) +
         "      if (warningTurn) actions.append(actionButton('Write the alert brief', () => drawers.alert(WGx, place, 1)));" + chr(10) +
         "      actions.append(actionButton('Write a briefing', () => drawers.briefing(WGx, place)));" + chr(10) +
         "    }" + chr(10) +
         "    const advisory = advisoryBriefParams(packet);" + chr(10) +
         "    if (advisory) actions.append(actionButton('Write the advisory brief', () => drawers.advisory(WGx, advisory)));" + chr(10) +
         "  }")
t = t.replace(old, added, 1)
p.write_text(t)
print('patched views.js actions')