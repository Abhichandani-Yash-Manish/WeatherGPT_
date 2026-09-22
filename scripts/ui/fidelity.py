"""Compare a rebuilt page against the design it replicates, with real pixels.

    python3 scripts/ui/fidelity.py --reference research/reviews/<dated-folder>/overview@1440.png \
                                   --capture   research/implementation/ui-evidence/light-overview@1440.png \
                                   --out       research/implementation/ui-evidence/diff-overview@1440

Reports, per image pair: the dimensions and whether they match, the share of pixels that differ beyond a
tolerance, the mean absolute difference, a ranked list of the worst grid regions (so the fix has an address),
and — when a reference palette is given — which reference colours the capture does not use.

The comparison is local and deterministic: Pillow, no service, no credentials.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw

def load(path):
    image = Image.open(path).convert('RGB')
    return image

def palette_of(image, colours=8):
    small = image.copy()
    small.thumbnail((240, 240))
    quantised = small.quantize(colors=colours, method=Image.Quantize.MEDIANCUT).convert('RGB')
    counts = {}
    for pixel in quantised.getdata():
        counts[pixel] = counts.get(pixel, 0) + 1
    total = sum(counts.values()) or 1
    return [{'hex': '#%02x%02x%02x' % pixel, 'share': round(count / total, 4)}
            for pixel, count in sorted(counts.items(), key=lambda item: -item[1])]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference', required=True)
    parser.add_argument('--capture', required=True)
    parser.add_argument('--out', default=None, help='directory for the heatmap and the JSON report')
    parser.add_argument('--tolerance', type=int, default=12, help='per-channel difference treated as equal')
    parser.add_argument('--grid', type=int, default=12, help='grid cells per axis for the ranked regions')
    parser.add_argument('--top', type=int, default=8)
    parser.add_argument('--expect-palette', default=None, help='JSON list of #rrggbb the design states')
    args = parser.parse_args()

    reference, capture = load(args.reference), load(args.capture)
    if reference.size != capture.size:
        capture = capture.resize(reference.size)
    difference = ImageChops.difference(reference, capture)
    grayscale = difference.convert('L')
    histogram = grayscale.histogram()
    total = sum(histogram) or 1
    within = sum(histogram[:args.tolerance + 1])
    significant = 1 - within / total
    mean = sum(index * count for index, count in enumerate(histogram)) / total

    width, height = reference.size
    cell_w, cell_h = max(1, width // args.grid), max(1, height // args.grid)
    regions = []
    pixels = grayscale.load()
    for row in range(args.grid):
        for column in range(args.grid):
            x0, y0 = column * cell_w, row * cell_h
            x1, y1 = min(width, x0 + cell_w), min(height, y0 + cell_h)
            if x1 <= x0 or y1 <= y0:
                continue
            total_cell = (x1 - x0) * (y1 - y0)
            heavy = 0
            for y in range(y0, y1, 2):
                for x in range(x0, x1, 2):
                    if pixels[x, y] > args.tolerance:
                        heavy += 1
            sampled = ((x1 - x0 + 1) // 2) * ((y1 - y0 + 1) // 2) or 1
            share = heavy / sampled
            if share > 0.02:
                regions.append({'row': row, 'column': column, 'x': x0, 'y': y0,
                                'width': x1 - x0, 'height': y1 - y0, 'differing_share': round(share, 4)})
    regions.sort(key=lambda item: -item['differing_share'])

    report = {
        'reference': str(args.reference), 'capture': str(args.capture),
        'reference_size': list(reference.size), 'capture_size': list(Image.open(args.capture).size),
        'identical_size': list(reference.size) == list(Image.open(args.capture).size),
        'pixels_differing_beyond_tolerance': round(significant, 4),
        'mean_absolute_difference': round(mean, 2),
        'tolerance': args.tolerance,
        'worst_regions': regions[:args.top],
        'reference_palette': palette_of(reference), 'capture_palette': palette_of(capture),
    }
    if args.expect_palette:
        expected = [value.lower() for value in json.loads(Path(args.expect_palette).read_text())]
        present = {row['hex'] for row in report['capture_palette']}
        report['palette_missing'] = [value for value in expected if value not in present]

    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        heat = Image.merge('RGB', (grayscale.point(lambda v: min(255, v * 3)), Image.new('L', reference.size, 0), Image.new('L', reference.size, 0)))
        annotated = Image.blend(reference, heat, 0.55)
        draw = ImageDraw.Draw(annotated)
        for region in regions[:args.top]:
            draw.rectangle([region['x'], region['y'], region['x'] + region['width'], region['y'] + region['height']], outline=(255, 0, 0), width=2)
        annotated.save(out / 'heatmap.png')
        (out / 'report.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
        print('wrote', out / 'heatmap.png', 'and', out / 'report.json')

    print('size:', report['reference_size'], 'vs', report['capture_size'], 'identical:', report['identical_size'])
    print('pixels differing beyond tolerance', args.tolerance, ':', round(significant * 100, 2), '%')
    print('mean absolute difference:', round(mean, 2), '/255')
    for region in regions[:args.top]:
        print('   region row', region['row'], 'col', region['column'], 'at', region['x'], region['y'],
              region['width'], 'x', region['height'], '->', round(region['differing_share'] * 100, 1), '% differing')
    if 'palette_missing' in report:
        print('reference colours absent from the capture:', report['palette_missing'] or 'none')
    return 0 if significant < 0.02 else 1

if __name__ == '__main__':
    sys.exit(main())
