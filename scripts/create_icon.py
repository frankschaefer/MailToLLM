#!/usr/bin/env python3
"""Generate application icon for MailToLLM."""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def create_icon():
    """Create a simple mail-themed icon."""
    # Icon sizes for macOS
    sizes = [16, 32, 64, 128, 256, 512, 1024]

    # Create output directory
    output_dir = Path(__file__).parent.parent / "src" / "mailtollm" / "resources"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create the largest size first
    size = 1024
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background gradient (blue theme)
    bg_color = (31, 42, 68)  # Dark blue from the app header
    accent_color = (100, 149, 237)  # Cornflower blue

    # Draw rounded rectangle background
    margin = size // 10
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=size // 8,
        fill=bg_color
    )

    # Draw mail envelope
    envelope_margin = size // 4
    envelope_top = size // 3
    envelope_bottom = size - envelope_margin
    envelope_left = envelope_margin
    envelope_right = size - envelope_margin

    # Envelope body (white)
    envelope_color = (255, 255, 255)
    draw.rectangle(
        [envelope_left, envelope_top, envelope_right, envelope_bottom],
        fill=envelope_color,
        outline=accent_color,
        width=size // 64
    )

    # Envelope flap (triangle)
    mid_x = size // 2
    flap_height = envelope_bottom - envelope_top
    flap_points = [
        (envelope_left, envelope_top),
        (mid_x, envelope_top + flap_height // 3),
        (envelope_right, envelope_top)
    ]
    draw.polygon(flap_points, fill=accent_color, outline=accent_color)

    # Draw small "AI" text at bottom
    try:
        # Try to use a nice font
        font_size = size // 12
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except:
        font = None

    text = "AI"
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_x = (size - text_width) // 2
    text_y = envelope_bottom - size // 6

    draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)

    # Save as PNG for window icon
    icon_png = output_dir / "icon.png"
    img.save(icon_png, 'PNG')
    print(f"Created: {icon_png}")

    # Create different sizes for .icns (macOS app bundle)
    iconset_dir = output_dir / "icon.iconset"
    iconset_dir.mkdir(exist_ok=True)

    for size in sizes:
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(iconset_dir / f"icon_{size}x{size}.png", 'PNG')
        # Also create @2x versions
        if size <= 512:
            resized_2x = img.resize((size * 2, size * 2), Image.Resampling.LANCZOS)
            resized_2x.save(iconset_dir / f"icon_{size}x{size}@2x.png", 'PNG')

    print(f"Created iconset: {iconset_dir}")
    print("\nTo create .icns file for macOS app bundle, run:")
    print(f"  iconutil -c icns {iconset_dir}")

    return icon_png

if __name__ == "__main__":
    create_icon()
