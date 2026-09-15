import pathlib
p = pathlib.Path('web/panels.js')
t = p.read_text()
start = t.index("    briefButton.addEventListener('click', async () => {")
end = t.index('    controls.append(stateSelect, search, briefButton);')
old = t[start:end]
assert 'alert-brief' in old, 'the inline composition was expected here'
new = ("    briefButton.addEventListener('click', () => {" + chr(10) +
       "      const W = window.WG;" + chr(10) +
       "      if (W && W.briefDrawers) W.briefDrawers.alert(W, place, 1);" + chr(10) +
       "    });" + chr(10))
t = t[:start] + new + t[end:]

# The briefcase gains the briefing action, so the engine's runner is reachable from the page.
anchor = "    const block = WGref.block('Kept briefs', entries.length + ' kept in the local store · ' + (view.delivery || 'local_only_no_delivery'));"
assert t.count(anchor) == 1, t.count(anchor)
tools_block = ("    const briefingTools = el('div', undefined, 'brief-tools');" + chr(10) +
               "    const writeBriefing = el('button', 'Write a briefing for the working place', 'ghost');" + chr(10) +
               "    writeBriefing.type = 'button';" + chr(10) +
               "    writeBriefing.setAttribute('aria-label', 'Compose a briefing for the working place and write it into the local series');" + chr(10) +
               "    writeBriefing.addEventListener('click', () => { const W = window.WG; if (W && W.briefDrawers) W.briefDrawers.briefing(W, null); });" + chr(10) +
               "    briefingTools.append(writeBriefing);" + chr(10) +
               "    block.append(briefingTools);" + chr(10))
t = t.replace(anchor, anchor + chr(10) + tools_block, 1)

# A briefing run re-renders the surface so the newest run appears without a manual reload.
old_drawer = "          body.append(uses);"
assert t.count(old_drawer) == 1, t.count(old_drawer)
t = t.replace(old_drawer, "          body.append(uses);" + chr(10) + "          if (typeof WGref.render === 'function') WGref.render();", 1)
p.write_text(t)
print('patched warnings panel and briefcase')