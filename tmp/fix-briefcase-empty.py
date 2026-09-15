import pathlib
p = pathlib.Path('web/panels.js')
t = p.read_text()
NL = chr(10)

empty_old = ("      block.append(WGref.stateBlock('plain', 'Nothing is kept yet.'," + NL +
            "        'Open Warnings and write the alert brief for the working place, then keep it here. A brief is composed from its sources by the server: this page cannot save a brief the workspace did not compose.'));" + NL +
            "      host.append(block);" + NL +
            "      return;" + NL)
assert t.count(empty_old) == 1, ('empty', t.count(empty_old))
empty_new = ("      block.append(WGref.stateBlock('plain', 'Nothing is kept yet.'," + NL +
            "        'Open Warnings and write the alert brief for the working place, then keep it here. A brief is composed from its sources by the server: this page cannot save a brief the workspace did not compose.'));" + NL)
t = t.replace(empty_old, empty_new, 1)

start = t.index("    const list = el('ul', undefined, 'brief-list');")
end = t.index("    host.append(block);" + NL + "    /* The briefing series is a local file series")
segment = t[start:end]
indented = NL.join(('  ' + line if line.strip() else line) for line in segment.splitlines())
wrapped = '    if (entries.length) {' + NL + indented + NL + '    }' + NL
t = t[:start] + wrapped + t[end:]
p.write_text(t)
print('patched')