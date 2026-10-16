"""The "notebook film" look for portraits: an instant-photo print that sits on the paper.

Warm, slightly faded tones, a paper-coloured split tone (warm highlights,
ink-blue shadows), fine film grain, the site's own paper texture and a soft
vignette. Colour and texture only: nothing about the subject is altered.
Pillow-only so it adds no dependency.
"""

from functools import lru_cache
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps

PAPER_TEXTURE = Path(settings.BASE_DIR) / "static" / "textures" / "grain.webp"


def _curve(lift: float, gain: float, gamma: float = 1.0):
    """Per-channel tone curve: lifted blacks (fade) and a gentle gain."""
    return [min(255, max(0, round(lift + (gain - lift) * ((i / 255) ** gamma)))) for i in range(256)]


@lru_cache(maxsize=1)
def _paper_tile() -> Image.Image | None:
    try:
        with Image.open(PAPER_TEXTURE) as tile:
            return tile.convert("RGBA")
    except OSError:
        return None


def _paper_overlay(size: tuple[int, int]) -> Image.Image | None:
    tile = _paper_tile()
    if tile is None:
        return None
    canvas = Image.new("RGBA", size, (255, 255, 255, 0))
    for x in range(0, size[0], tile.width):
        for y in range(0, size[1], tile.height):
            canvas.alpha_composite(tile, (x, y))
    white = Image.new("RGBA", size, (255, 255, 255, 255))
    return Image.alpha_composite(white, canvas).convert("RGB")


def film_look(image: Image.Image, strength: float = 1.0) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert("RGB")
    original = image
    w, h = image.size

    # 1. Softer colour and contrast, like an instant print
    image = ImageEnhance.Color(image).enhance(0.86)
    image = ImageEnhance.Contrast(image).enhance(0.97)

    # 2. Split tone: warm paper highlights, lifted ink-blue shadows
    r = _curve(lift=16, gain=255, gamma=0.92)
    g = _curve(lift=14, gain=246, gamma=0.98)
    b = _curve(lift=22, gain=224, gamma=1.02)
    image = image.point(r + g + b)

    # 3. Fine film grain (monochrome, slightly soft)
    noise = Image.effect_noise((w, h), 26).filter(ImageFilter.GaussianBlur(0.45))
    grain = Image.merge("RGB", (noise, noise, noise))
    image = Image.blend(image, ImageChops.overlay(image, grain), 0.36)

    # 4. The site's paper texture, pressed in lightly
    paper = _paper_overlay((w, h))
    if paper is not None:
        image = Image.blend(image, ImageChops.multiply(image, paper), 0.55)

    # 5. Soft vignette towards warm ink
    mask = Image.radial_gradient("L").resize((w, h), Image.Resampling.BICUBIC)
    mask = mask.point(lambda v: max(0, min(255, int((v - 110) * 1.25))))
    edge = Image.new("RGB", (w, h), (58, 46, 34))
    image = Image.composite(Image.blend(image, edge, 0.55), image, mask.point(lambda v: int(v * 0.7)))

    if strength < 1:
        image = Image.blend(original, image, strength)
    return image
