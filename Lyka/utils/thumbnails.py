import os
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat
from youtubesearchpython.__future__ import VideosSearch
from config import FAILED

# Constants
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

WIDTH, HEIGHT = 800, 450
FONT_PATH_TITLE = "Lyka/assets/font.ttf"
FONT_PATH_META = "Lyka/assets/cfont.ttf"
FALLBACK_PATH = "Lyka/assets/fallback.jpg"

def truncate_text(text, font, max_width):
    if font.getlength(text) <= max_width:
        return text
    ellipsis = "..."
    for i in range(len(text), 0, -1):
        truncated = text[:i].strip() + ellipsis
        if font.getlength(truncated) <= max_width:
            return truncated
    return ellipsis

def is_bright(image: Image.Image) -> bool:
    stat = ImageStat.Stat(image.convert("L"))
    return stat.mean[0] > 130  # brightness threshold

async def gen_thumb(videoid: str) -> str:
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_lyka.png")
    if os.path.exists(cache_path):
        return cache_path

    results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
    try:
        data = (await results.next())["result"][0]
        title = data.get("title", "Unknown Title")
        channel = data.get("channel", {}).get("name", "Unknown Channel")
        thumbnail = data.get("thumbnails", [{}])[0].get("url", FAILED)
        duration = data.get("duration") or "Live"
    except Exception:
        title, channel, thumbnail, duration = "Unknown Title", "Unknown Channel", FAILED, "Live"

    is_live = duration.strip().lower() in {"", "live", "live now"}
    duration_text = "Live" if is_live else duration

    thumb_path = os.path.join(CACHE_DIR, f"thumb_{videoid}.png")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    async with aiofiles.open(thumb_path, "wb") as f:
                        await f.write(await resp.read())
    except Exception:
        thumb_path = FALLBACK_PATH

    try:
        art = Image.open(thumb_path).resize((200, 200)).convert("RGBA")
        background_art = Image.open(thumb_path).resize((WIDTH, HEIGHT)).convert("RGBA")
    except Exception:
        art = Image.open(FALLBACK_PATH).resize((200, 200)).convert("RGBA")
        background_art = Image.open(FALLBACK_PATH).resize((WIDTH, HEIGHT)).convert("RGBA")

    # Base background
    bg = background_art.filter(ImageFilter.GaussianBlur(25))

    # Panel details
    card_x, card_y = 100, 100
    card_w, card_h = 600, 250
    card_radius = 50
    panel_box = (card_x, card_y, card_x + card_w, card_y + card_h)

    # Frosted glass panel
    frosted = bg.crop(panel_box).filter(ImageFilter.GaussianBlur(6))
    brightness_sample = frosted.copy().resize((1, 1))
    panel_bright = is_bright(brightness_sample)

    # Switch glass overlay to dark if bright (text color stays same)
    overlay_color = (0, 0, 0, 100) if panel_bright else (255, 255, 255, 60)
    overlay = Image.new("RGBA", (card_w, card_h), overlay_color)
    panel = Image.alpha_composite(frosted, overlay)

    # Rounded mask
    mask = Image.new("L", (card_w, card_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, card_w, card_h), card_radius, fill=255)

    # Paste glass panel
    bg.paste(panel, (card_x, card_y), mask)

    draw = ImageDraw.Draw(bg)

    # Text color (now fixed, no change)
    text_color = (255, 255, 255)
    subtext_color = (200, 200, 200)

    # Fonts
    try:
        title_font = ImageFont.truetype(FONT_PATH_TITLE, 34)
        meta_font = ImageFont.truetype(FONT_PATH_META, 28)
        small_font = ImageFont.truetype(FONT_PATH_META, 24)
    except OSError:
        title_font = meta_font = small_font = ImageFont.load_default()

    # Album Thumbnail
    art_size = 140
    thumb = art.resize((art_size, art_size))
    thumb_mask = Image.new("L", (art_size, art_size), 0)
    ImageDraw.Draw(thumb_mask).rounded_rectangle((0, 0, art_size, art_size), 40, fill=255)
    thumb_x = card_x + 40
    thumb_y = card_y + (card_h - art_size) // 2
    bg.paste(thumb, (thumb_x, thumb_y), thumb_mask)

    # Text
    text_x = thumb_x + art_size + 40
    max_title_width = card_w - (art_size + 120)

    draw.text((text_x, card_y + 30), "Levy Vibez", font=small_font, fill=subtext_color)
    draw.text((text_x, card_y + 70), truncate_text(title, title_font, max_title_width), font=title_font, fill=text_color)
    draw.text((text_x, card_y + 120), channel.strip(), font=meta_font, fill=subtext_color)

    # Play button
    play_size = 44
    p_x = text_x
    p_y = card_y + 170

    draw.ellipse((p_x, p_y, p_x + play_size, p_y + play_size), fill=text_color)
    triangle = [
        (p_x + 16, p_y + 12),
        (p_x + 16, p_y + play_size - 12),
        (p_x + play_size - 12, p_y + play_size // 2)
    ]
    triangle_fill = (240, 240, 240) if text_color == (30, 30, 30) else (30, 30, 40)
    draw.polygon(triangle, fill=triangle_fill)

    draw.text((p_x + play_size + 20, p_y + 8), f"00:00 — {duration_text}", font=small_font, fill=subtext_color)

    try:
        os.remove(thumb_path)
    except Exception:
        pass

    bg.save(cache_path)
    return cache_path
