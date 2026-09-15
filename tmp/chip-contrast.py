import colorsys
def rgb(h):
    h = h.lstrip('#'); return tuple(int(h[i:i+2], 16)/255 for i in (0,2,4))
def lum(h):
    f = lambda c: c/12.92 if c <= 0.03928 else ((c+0.055)/1.055)**2.4
    r,g,b = rgb(h); return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b)
def ratio(a,b):
    la,lb = lum(a),lum(b); hi,lo = max(la,lb),min(la,lb); return (hi+0.05)/(lo+0.05)
def to_hex(h,l,s):
    r,g,b = colorsys.hls_to_rgb(h,l,s)
    return '#%02x%02x%02x' % tuple(round(max(0,min(1,v))*255) for v in (r,g,b))
def darken(value, wash, target=4.5):
    h,l,s = colorsys.rgb_to_hls(*rgb(value))
    for step in range(1, 400):
        cand = to_hex(h, max(0.0, l-step/1000.0), s)
        if ratio(cand, wash) >= target + 0.1:
            return cand, ratio(cand, wash)
    return value, ratio(value, wash)
pairs = [('--red', '#b22b2b', '--red-wash', '#f8e3e1'), ('--orange', '#b25e12', '--orange-wash', '#f9ebdb'),
         ('--yellow', '#8a6c00', '--yellow-wash', '#f7f0d5'), ('--green', '#2c6e45', '--green-wash', '#e1efe6')]
for name, value, wash_name, wash in pairs:
    now = ratio(value, wash)
    cand, got = darken(value, wash)
    print('%-9s %s on %s -> %.2f | candidate %s -> %.2f' % (name, value, wash, now, cand, got))
print()
print('dark theme chips (on dark washes):')
for name, value, wash in [('--red', '#ff7a72', '#3a1b1b'), ('--orange', '#f0a35a', '#38260f'), ('--yellow', '#e6c85e', '#373012'), ('--green', '#6fc592', '#12301f')]:
    print('  %-9s %s on %s -> %.2f' % (name, value, wash, ratio(value, wash)))
print()
print('chip borders vs washes (non-text contrast, decorative):')
for value, wash in [('#b25e12','#f9ebdb'), ('#8a6c00','#f7f0d5')]:
    print('  ', value, wash, '%.2f' % ratio(value, wash))
