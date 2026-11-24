"""Stitch the app's offline Sentinel-2 base map (zoom 14) and draw the 99 watched lakes on it."""
import io, json, math, sys, zipfile
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

ZIP, ASSETS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
Z = 14
z = zipfile.ZipFile(ZIP)
tiles = {}
for n in z.namelist():
    p = n.split('/')
    if len(p) == 3 and p[0] == str(Z) and p[2].endswith('.jpg'):
        tiles[(int(p[1]), int(p[2][:-4]))] = n
xs = [k[0] for k in tiles]; ys = [k[1] for k in tiles]
x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
W, H = (x1 - x0 + 1) * 256, (y1 - y0 + 1) * 256
mos = Image.new('RGB', (W, H), 'black')
for (x, y), n in tiles.items():
    mos.paste(Image.open(io.BytesIO(z.read(n))).convert('RGB'), ((x - x0) * 256, (y - y0) * 256))

def px(lon, lat):
    n = 2 ** Z
    fx = (lon + 180) / 360 * n
    fy = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return ((fx - x0) * 256, (fy - y0) * 256)

# Find the black margins (no imagery) and crop to the imaged area
gray = mos.convert('L').point(lambda v: 255 if v > 8 else 0)
bbox = gray.getbbox(); print('imaged bbox', bbox, 'of', (W, H))

lakes = json.load(open(ASSETS, encoding='utf-8'))['features']
rings = []
for f in lakes:
    g = f['geometry']
    polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
    for poly in polys:
        rings.append([px(lon, lat) for lon, lat in poly[0]])

# Graded base: a touch more contrast and saturation for print
base = ImageEnhance.Contrast(mos).enhance(1.12)
base = ImageEnhance.Color(base).enhance(1.15)
base.crop(bbox).save(f'{OUT}/s2-hyderabad.jpg', quality=88)

# Lakes overlay: soft glow plus crisp outline and translucent fill
glow = Image.new('RGBA', (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
for r in rings: gd.line(r + [r[0]], fill=(80, 230, 255, 255), width=14)
glow = glow.filter(ImageFilter.GaussianBlur(10))
over = Image.new('RGBA', (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(over)
for r in rings:
    od.polygon(r, fill=(64, 210, 255, 90))
    od.line(r + [r[0]], fill=(120, 240, 255, 255), width=4)
dark = ImageEnhance.Brightness(base).enhance(0.62).convert('RGBA')
lk = Image.alpha_composite(Image.alpha_composite(dark, glow), over).convert('RGB')
lk.crop(bbox).save(f'{OUT}/s2-hyderabad-lakes.jpg', quality=88)
print('lakes drawn', len(rings))
