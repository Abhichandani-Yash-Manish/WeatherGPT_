import pathlib
p = pathlib.Path('web/views.js')
t = p.read_text()

anchor = 'function renderRetrievalAccount(packet) {'
assert t.count(anchor) == 1
helper = ("/* views.js builds its own small tables; the shared one lives on WG. The retrieval account" + chr(10) +
          "   used a bare `table(...)` call and threw 'table is not defined' in the page, which stopped the" + chr(10) +
          "   whole turn from rendering - found in the browser pass on 15 September 2026. */" + chr(10) +
          "function accountTable(head, rows) {" + chr(10) +
          "  const maker = (window.WG && window.WG.table) || null;" + chr(10) +
          "  if (maker) return maker(head, rows);" + chr(10) +
          "  const node = el('table', undefined, 'account-table');" + chr(10) +
          "  const headRow = el('tr');" + chr(10) +
          "  head.forEach(cell => headRow.append(el('th', cell)));" + chr(10) +
          "  node.append(headRow);" + chr(10) +
          "  (rows || []).forEach(row => { const tr = el('tr'); row.forEach(cell => tr.append(el('td', cell))); node.append(tr); });" + chr(10) +
          "  return node;" + chr(10) + "}" + chr(10) + chr(10) + anchor)
t = t.replace(anchor, helper, 1)
t = t.replace('box.append(table([\'Field\', \'Value\', \'Provenance\'], rows));', 'box.append(accountTable([\'Field\', \'Value\', \'Provenance\'], rows));', 1)
t = t.replace('box.append(table([\'Field\', \'Value\', \'Provenance\'], [', 'box.append(accountTable([\'Field\', \'Value\', \'Provenance\'], [', 1)
t = t.replace('box.append(table([\'Edition\', \'Region\', \'Printed issue\', \'Currency and age\'], editions.map(item => [', 'box.append(accountTable([\'Edition\', \'Region\', \'Printed issue\', \'Currency and age\'], editions.map(item => [', 1)
p.write_text(t)
assert 'table([' not in t, 'a bare table call remains'
print('retrieval account uses the shared table helper')