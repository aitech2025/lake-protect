"""Cut the deck's images from the Sentinel-2 mosaics (mosaic.py) and the app screenshots.

Usage: py -I pitch/build/deck_images.py <dir with mosaics> <dir with app screenshots>
"""
import sys
from pathlib import Path
from PIL import Image, ImageEnhance

Image.MAX_IMAGE_PIXELS = None
SRC, SHOTS = Path(sys.argv[1]), Path(sys.argv[2])
OUT = Path(__file__).resolve().parent.parent / "img"
OUT.mkdir(exist_ok=True)


def save(im: Image.Image, name: str, size: tuple[int, int], q: int = 82) -> None:
    im = im.convert("RGB").resize(size, Image.LANCZOS)
    im.save(OUT / name, quality=q, optimize=True, progressive=True)
    print(name, size, (OUT / name).stat().st_size // 1024, "KB")


def crop_ratio(im: Image.Image, ratio: float, cx: float = .5, cy: float = .5) -> Image.Image:
    w, h = im.size
    if w / h > ratio:
        nw = int(h * ratio); x = int((w - nw) * cx); return im.crop((x, 0, x + nw, h))
    nh = int(w / ratio); y = int((h - nh) * cy); return im.crop((0, y, w, y + nh))


plain = Image.open(SRC / "s2-hyderabad.jpg")
lakes = Image.open(SRC / "s2-hyderabad-lakes.jpg")
save(crop_ratio(plain, 16 / 9, cy=.45), "hero-hyderabad.jpg", (1920, 1080), 78)
save(crop_ratio(lakes, 16 / 9, cy=.45), "lakes-wide.jpg", (1920, 1080), 78)
save(crop_ratio(lakes, 0.8, cx=.45), "lakes-tall.jpg", (1000, 1250), 80)

desk = Image.open(SHOTS / "real-kapra.png")
save(desk, "app-desk-kapra.jpg", (1600, 1000), 86)
mon = Image.open(SHOTS / "monthly.png")
save(mon, "app-monthly.jpg", (1600, 1000), 86)
field = Image.open(SHOTS / "field2-alert-tel.png")
save(field, "app-field-te.jpg", (585, 1266), 86)
