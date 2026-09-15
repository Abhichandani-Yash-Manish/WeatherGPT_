import io, pathlib, re
p = pathlib.Path('weathergpt_data/workspace.py')
text = p.read_text()
anchor = "if path=='/api/advisories/brief':return self.respond(200,workspace.advisory_brief(parse_qs(urlsplit(self.path).query)))"
assert text.count(anchor) == 1, text.count(anchor)
extra = (
    "\n                    if path=='/api/briefs':return self.respond(200,workspace.briefs())"
    "\n                    if path in ('/api/briefs/get','/api/briefs/export'):"
    "\n                        brief_id=(parse_qs(urlsplit(self.path).query).get('id') or [''])[0]"
    "\n                        if not brief_id:raise ValueError('Give the identifier of the kept brief')"
    "\n                        if path=='/api/briefs/get':return self.respond(200,workspace.saved_brief(brief_id))"
    "\n                        name,text=workspace.brief_export(brief_id)"
    "\n                        return self.respond(200,text,'text/markdown',filename=name)")
text = text.replace(anchor, anchor + extra, 1)
route_anchor = "'/api/watches/check':workspace.check_watches,"
assert text.count(route_anchor) == 1
text = text.replace(route_anchor, route_anchor + "'/api/briefs/save':workspace.save_brief,\n                    '/api/briefs/delete':workspace.delete_brief,", 1)
p.write_text(text)
print('done')
