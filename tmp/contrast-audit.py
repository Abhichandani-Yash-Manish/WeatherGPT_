import colorsys
def rgb(hexstr):
    h = hexstr.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))
def lum(hexstr):
    def channel(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb(hexstr)
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)
def hsl(hexstr):
    r, g, b = rgb(hexstr)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h, l, s
def to_hex(h, l, s):
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return '#%02x%02x%02x' % tuple(round(max(0, min(1, v)) * 255) for v in (r, g, b))
def darken_to(hexstr, backgrounds, target=4.6):
    h, l, s = hsl(hexstr)
    best = hexstr
    for step in range(1, 400):
        cand = to_hex(h, max(0.0, l - step / 1000.0), s)
        if all(ratio(cand, bg) >= target for bg in backgrounds):
            return cand, min(ratio(cand, bg) for bg in backgrounds)
    return best, min(ratio(best, bg) for bg in backgrounds)
def lighten_to(hexstr, backgrounds, target=4.6):
    h, l, s = hsl(hexstr)
    for step in range(1, 400):
        cand = to_hex(h, min(1.0, l + step / 1000.0), s)
        if all(ratio(cand, bg) >= target for bg in backgrounds):
            return cand, min(ratio(cand, bg) for bg in backgrounds)
    return hexstr, 0

light_surfaces = ['#ecf0ec', '#fbfcfa', '#e2e9e4', '#dcebeb', '#f0ead9', '#f8e3e1', '#f9ebdb', '#f7f0d5', '#e1efe6']
dark_surfaces = ['#0b1216', '#121c21', '#0e171c', '#123236', '#2f2a17', '#3a1b1b', '#38260f', '#373012', '#12301f']
print('light theme')
for token, value in [('--mute', '#697c81'), ('--ink-soft', '#3d525b'), ('--slate', '#33506a'), ('--data', '#0d6d77'), ('--line-strong', '#b7c5bd')]:
    worst = min(light_surfaces, key=lambda bg: ratio(value, bg))
    print('  %-12s %s worst %.2f:%s' % (token, value, ratio(value, worst), worst))
cand, got = darken_to('#697c81', light_surfaces)
print('  -> --mute candidate', cand, 'min contrast %.2f' % got)
cand2, got2 = darken_to('#33506a', light_surfaces)
print('  -> --slate candidate', cand2, 'min contrast %.2f' % got2)
print('dark theme')
for token, value in [('--mute', '#81979d'), ('--ink-soft', '#b2c3c1'), ('--slate', '#9db6cd'), ('--data', '#4fb3be'), ('--housing-mute', '#7e959a'), ('--housing-ink', '#d8e4e1')]:
    worst = min(dark_surfaces, key=lambda bg: ratio(value, bg))
    print('  %-12s %s worst %.2f:%s' % (token, value, ratio(value, worst), worst))
cand3, got3 = lighten_to('#81979d', dark_surfaces)
print('  -> --mute candidate', cand3, 'min contrast %.2f' % got3)
cand4, got4 = lighten_to('#4fb3be', dark_surfaces)
print('  -> --data candidate', cand4, 'min contrast %.2f' % got4)
print('housing (both themes)')
for label, value, bgs in [('housing-ink light', '#dbe6e2', ['#101a20', '#16242c']), ('housing-mute light', '#8ba0a2', ['#101a20', '#16242c']),
                          ('housing-ink dark', '#d8e4e1', ['#070d10', '#0f191e']), ('housing-mute dark', '#7e959a', ['#070d10', '#0f191e'])]:
    print('  %-20s %s min %.2f' % (label, value, min(ratio(value, bg) for bg in bgs)))
cand5, got5 = lighten_to('#8ba0a2', ['#101a20', '#16242c'])
print('  -> housing-mute light candidate', cand5, 'min %.2f' % got5)
