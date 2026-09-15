import pathlib
p = pathlib.Path('weathergpt_data/workspace.py')
text = p.read_text()
block = ("                    if path=='/api/briefs':return self.respond(200,workspace.briefs())"
         "\n                    if path in ('/api/briefs/get','/api/briefs/export'):"
         "\n                        brief_id=(parse_qs(urlsplit(self.path).query).get('id') or [''])[0]"
         "\n                        if not brief_id:raise ValueError('Give the identifier of the kept brief')"
         "\n                        if path=='/api/briefs/get':return self.respond(200,workspace.saved_brief(brief_id))"
         "\n                        name,text=workspace.brief_export(brief_id)"
         "\n                        return self.respond(200,text,'text/markdown',filename=name)")
assert text.count(block) == 2, text.count(block)
text = text.replace(block + block, block, 1)
assert text.count(block) == 1
p.write_text(text)
print('deduped')
