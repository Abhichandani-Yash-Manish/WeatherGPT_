import pathlib
p = pathlib.Path('research/implementation/coastal-and-typo-repairs-20260915/journey.md')
t = p.read_text()
marker = '## What this does not establish'
head = t.split(marker)[0]
tail = (marker + chr(10) + chr(10) +
        '- No accuracy claim about place resolution in general: two typo patterns and one coast shape were measured.' + chr(10) +
        '- A coast question still asks for a district or a port, because the official district product has nothing to match for a sea area and the sea-area bulletins remain unconnected.' + chr(10) +
        '- A single approximate match still asks for confirmation rather than being accepted silently; the answer offers one named candidate instead of twenty.' + chr(10) +
        '- No usability, native-language or mobile acceptance was measured.' + chr(10))
p.write_text(head + tail)
print('fixed')