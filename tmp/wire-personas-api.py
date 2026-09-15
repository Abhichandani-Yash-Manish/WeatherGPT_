import pathlib
p = pathlib.Path('weathergpt_data/product_api.py')
text = p.read_text()

old = "                 '/api/climate/index', '/api/climate/series', '/api/advisories/states',\n                 '/api/advisories/districts')"
assert text.count(old) == 1, text.count(old)
text = text.replace(old, "                 '/api/climate/index', '/api/climate/series', '/api/advisories/states',\n                 '/api/advisories/districts', '/api/personas')", 1)

old_dispatch = "    if path == '/api/places/search':"
assert text.count(old_dispatch) == 1
branch = ("    if path == '/api/personas':\n"
          "        return personas_view()\n"
          "    if path == '/api/places/search':")
text = text.replace(old_dispatch, branch, 1)

view = ('''def personas_view():
    """Who is reading: three registered positions, each framing and never finding."""
    from .personas import PERSONA_NOTE, catalogue
    return envelope('personas.catalogue', 'ok', catalogue(),
                    limitations=[PERSONA_NOTE,
                                 'The same question under two personas retrieves the same evidence; only the emphasis, the '
                                 'starting surfaces and the listed limits differ.'])


''')
anchor = "def registry_products():"
assert text.count(anchor) == 1
text = text.replace(anchor, view + anchor, 1)
p.write_text(text)
print('patched')
