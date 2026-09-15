import pathlib
p = pathlib.Path('web/shell.js')
t = p.read_text()
anchor = "    paintHealthMini();"
assert t.count(anchor) == 1, t.count(anchor)
addition = ("    paintHealthMini();" + chr(10) +
            "    /* Ask the server to read the slow layers for the place this page is working with, so the" + chr(10) +
            "       first question is not the first read. It is a background read of the same governed adapters;" + chr(10) +
            "       the page does not wait for it and nothing is inferred from it. */" + chr(10) +
            "    (function warmWorkingPlace() {" + chr(10) +
            "      const place = WG.state.place || {};" + chr(10) +
            "      if (place.latitude === undefined || place.longitude === undefined) return;" + chr(10) +
            "      post('/api/warm', { lat: place.latitude, lon: place.longitude, label: place.label }).catch(function () { return null; });" + chr(10) +
            "    })();")
t = t.replace(anchor, addition, 1)
p.write_text(t)
print('page warms its working place')