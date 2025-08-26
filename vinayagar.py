#!/usr/bin/env python3

"""
Python CLI to Create Vinayagar Chaturthi Greeting with Your Name
Author: Santhosh Kumar
"""

import argparse, os, sys, platform, subprocess, shutil, re, urllib.request
from PIL import Image, ImageDraw, ImageFont

# === Constants ===
WIDTH, HEIGHT = 1080, 1080
FOOTER_HEIGHT = 150
HEADER_HEIGHT = 150
FONT_URL = "https://github.com/google/fonts/raw/refs/heads/main/ofl/hindmadurai/HindMadurai-Bold.ttf"
FONT_NAME = "HindMadurai-Bold.ttf"
GANESH_IMAGE = "vinayagar.png"

# Twemoji sources (PNG/72x72)
TWEMOJI_URLS = {
    "lamp": "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1fa94.png",   # 🪔 diya lamp
    "sparkle": "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/2728.png"   # ✨ sparkles
}

# Local filenames
HEADER_EMOJI = "twemoji_lamp.png"
FOOTER_EMOJI = "twemoji_sparkle.png"

# === Validation ===
def validate_name(name: str) -> str:
    name = name.strip()
    if not (2 <= len(name) <= 30):
        raise argparse.ArgumentTypeError("❌ Name must be 2–30 characters.")
    if not re.match(r"^[A-Za-z0-9\s.,'-\u0B80-\u0BFF]+$", name):
        raise argparse.ArgumentTypeError("❌ Name contains invalid characters.")
    return name

# === Download helper ===
def ensure_icon(local_file: str, url: str):
    if not os.path.exists(local_file):
        try:
            print(f"📥 Downloading emoji icon: {local_file}")
            urllib.request.urlretrieve(url, local_file)
        except Exception as e:
            print(f"⚠ Could not download emoji {local_file}: {e}")

# === Font Handling ===
def get_font_path() -> str:
    font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), FONT_NAME)
    if not os.path.exists(font_path):
        print("📥 Downloading HindMadurai font...")
        try:
            urllib.request.urlretrieve(FONT_URL, font_path)
            print("✅ Font downloaded.")
        except Exception as e:
            print(f"⚠ Font download failed: {e}")
            return ""
    return font_path

# === Text with Outline ===
def draw_text_with_outline(draw, position, text, font, fill, outline_color, outline_width=2):
    x, y = position
    for dx in range(-outline_width, outline_width+1):
        for dy in range(-outline_width, outline_width+1):
            if dx != 0 or dy != 0:
                draw.text((x+dx, y+dy), text, font=font, fill=outline_color)
    draw.text((x, y), text, font=font, fill=fill)

# === Paste Emoji PNG ===
def paste_icon(base_img: Image.Image, icon_path: str, x: int, y: int, size: int = 60):
    try:
        icon = Image.open(icon_path).convert("RGBA")
        icon = icon.resize((size, size), Image.LANCZOS)
        base_img.paste(icon, (x, y), icon)
    except Exception as e:
        print(f"⚠ Could not place emoji icon {icon_path}: {e}")

# === Add Radial Glow Behind Ganesh ===
def add_radial_glow(base_img: Image.Image, cx: int, cy: int, max_radius: int = 250):
    glow = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)

    for r in range(max_radius, 0, -10):
        alpha = int(180 * (r / max_radius))  # fade outward
        color = (255, 223, 128, max(0, 255 - alpha))  # soft golden
        glow_draw.ellipse(
            [cx-r, cy-r, cx+r, cy+r],
            fill=color
        )

    base_img.alpha_composite(glow)

# === Place Ganesh Image ===
def place_ganesh_image(base_img: Image.Image, cx: int, cy: int, scale: float = 0.35):
    try:
        ganesh = Image.open(GANESH_IMAGE).convert("RGBA")
        new_w = int(WIDTH * scale)
        aspect_ratio = ganesh.height / ganesh.width
        new_h = int(new_w * aspect_ratio)
        ganesh = ganesh.resize((new_w, new_h), Image.LANCZOS)

        # add smaller glow (0.7 * width)
        add_radial_glow(base_img, cx, cy, max_radius=int(new_w * 0.7))

        pos_x = cx - new_w // 2
        pos_y = cy - new_h // 2
        base_img.paste(ganesh, (pos_x, pos_y), ganesh)
    except Exception as e:
        print(f"⚠ Could not place Ganesh image: {e}")

# === Main Creator ===
def create_vinayagar_card(name: str, output_path: str):
    img = Image.new("RGBA", (WIDTH, HEIGHT), (255, 249, 196, 255))
    draw = ImageDraw.Draw(img)

    # Gradient background
    top_color = (255, 204, 229)
    bottom_color = (153, 102, 204)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    # Fonts
    font_path = get_font_path()
    font_header = ImageFont.truetype(font_path, 50) if font_path else ImageFont.load_default()
    font_footer = ImageFont.truetype(font_path, 50) if font_path else ImageFont.load_default()

    # Header
    header_text = "Happy Vinayagar Chaturthi"
    tw, th = draw.textsize(header_text, font=font_header)
    header_x, header_y = (WIDTH - tw) // 2, 80
    draw_text_with_outline(draw, (header_x, header_y), header_text,
                           font_header, fill="#772041", outline_color="#F0DDD7", outline_width=3)

    # Emoji icons (🪔 lamp left/right)
    paste_icon(img, HEADER_EMOJI, header_x - 80, header_y - 5, size=65)
    paste_icon(img, HEADER_EMOJI, header_x + tw + 15, header_y - 5, size=65)

    # Ganesh image with smaller glow at center
    place_ganesh_image(img, WIDTH//2, HEIGHT//2)

    # Footer (name + ✨ sparkles)
    tw, th = draw.textsize(name, font=font_footer)
    footer_y = HEIGHT - FOOTER_HEIGHT + 30
    footer_x = (WIDTH - tw) // 2
    draw_text_with_outline(draw, (footer_x, footer_y), name,
                           font_footer, fill="#1A7220", outline_color="#F5E2A5", outline_width=3)

    paste_icon(img, FOOTER_EMOJI, footer_x - 60, footer_y, size=50)
    paste_icon(img, FOOTER_EMOJI, footer_x + tw + 15, footer_y, size=50)

    img.save(output_path, "PNG")
    return output_path

# === Open Image ===
def open_image(path: str):
    try:
        sys_platform = platform.system()
        if sys_platform == "Darwin":
            subprocess.run(["open", path], check=False)
        elif sys_platform == "Windows":
            os.startfile(path)  # type: ignore
        elif sys_platform == "Linux":
            if "com.termux" in os.getenv("PREFIX", ""):
                if shutil.which("termux-open"):
                    subprocess.run(["termux-open", path], check=False)
                else:
                    print(f"⚠ termux-open not found. Image saved at: {path}")
            else:
                if shutil.which("xdg-open"):
                    subprocess.run(["xdg-open", path], check=False)
                else:
                    print(f"⚠ xdg-open not found. Image saved at: {path}")
        else:
            print(f"⚠ Unsupported platform. Image saved at: {path}")
    except Exception as e:
        print(f"⚠ Could not open image: {e}")

# === CLI Entrypoint ===
def main():
    parser = argparse.ArgumentParser(description="Create Vinayagar Chaturthi Greeting")
    parser.add_argument("name", type=validate_name, help="Footer name (in English)")
    parser.add_argument("-o", "--output", default="vinayagar.png", help="Output file name")
    args = parser.parse_args()

    # Ensure emoji icons downloaded
    ensure_icon(HEADER_EMOJI, TWEMOJI_URLS["lamp"])
    ensure_icon(FOOTER_EMOJI, TWEMOJI_URLS["sparkle"])

    # Downloads dir
    sys_platform = platform.system()
    if sys_platform == "Linux" and "com.termux" in os.getenv("PREFIX", ""):
        termux_paths = [
            os.path.expanduser("~/storage/downloads"),
            os.path.expanduser("~/storage/Download")
        ]
        downloads_dir = next((p for p in termux_paths if os.path.isdir(p)), termux_paths[0])
    elif sys_platform in ("Linux", "Windows", "Darwin"):
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    else:
        downloads_dir = os.path.expanduser("~")

    os.makedirs(downloads_dir, exist_ok=True)
    output_path = os.path.join(downloads_dir, args.output)

    try:
        path = create_vinayagar_card(args.name, output_path)
        print(f"✅ Greeting saved at {path}")
        open_image(path)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
