#!/usr/bin/env python3
"""Image generation utility using Pillow.

Provides simple image generation capabilities:
- Text-on-image (for notifications, status updates)
- Basic charts (bar charts, simple data visualization)
- Colored banners with text

Usage:
    from generate_image import generate_text_image, generate_bar_chart, generate_banner

Or as MCP tool via server.py:
    generate_image(text="Hello World", output_path="/tmp/hello.png")
"""

import os
from pathlib import Path
from typing import Optional

try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


def _ensure_pillow():
    if not PILLOW_AVAILABLE:
        raise RuntimeError(
            "Pillow is not installed. Run: pip install Pillow --break-system-packages"
        )


def _get_font(size: int = 24):
    """Try to load a reasonable font, fall back to default."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    # Fall back to default bitmap font
    return ImageFont.load_default()


def generate_text_image(
    text: str,
    output_path: str,
    width: int = 800,
    height: int = 400,
    bg_color: tuple = (30, 30, 50),
    text_color: tuple = (220, 220, 255),
    font_size: int = 32,
    title: Optional[str] = None,
) -> str:
    """Generate an image with text content.

    Args:
        text: Main body text to display (supports newlines)
        output_path: Where to save the image (PNG)
        width: Image width in pixels (default 800)
        height: Image height in pixels (default 400)
        bg_color: Background color as RGB tuple (default dark navy)
        text_color: Text color as RGB tuple (default light blue-white)
        font_size: Font size for body text (default 32)
        title: Optional title text (displayed larger at top)

    Returns:
        Path to the saved image file.
    """
    _ensure_pillow()

    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    margin = 40
    y = margin

    # Draw title if provided
    if title:
        title_font = _get_font(font_size + 12)
        draw.text((margin, y), title, font=title_font, fill=(255, 200, 100))
        # Move y down past title
        bbox = draw.textbbox((margin, y), title, font=title_font)
        y = bbox[3] + 20
        # Separator line
        draw.line([(margin, y), (width - margin, y)], fill=(100, 100, 150), width=2)
        y += 20

    # Draw body text with word wrapping
    body_font = _get_font(font_size)
    max_width = width - (margin * 2)

    lines = text.split("\n")
    for line in lines:
        if not line.strip():
            y += font_size // 2
            continue

        # Simple word wrap
        words = line.split()
        current_line = ""
        for word in words:
            test_line = (current_line + " " + word).strip() if current_line else word
            bbox = draw.textbbox((0, 0), test_line, font=body_font)
            line_width = bbox[2] - bbox[0]
            if line_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    draw.text((margin, y), current_line, font=body_font, fill=text_color)
                    y += font_size + 6
                current_line = word

        if current_line:
            draw.text((margin, y), current_line, font=body_font, fill=text_color)
            y += font_size + 6

        # Check if we've run out of space
        if y > height - margin:
            draw.text((margin, y), "...", font=body_font, fill=(150, 150, 150))
            break

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "PNG")
    return str(output_path)


def generate_bar_chart(
    data: dict,
    output_path: str,
    title: str = "Chart",
    width: int = 800,
    height: int = 500,
    bar_color: tuple = (70, 130, 180),
    bg_color: tuple = (240, 240, 250),
) -> str:
    """Generate a simple horizontal or vertical bar chart.

    Args:
        data: Dict of {label: value} pairs
        output_path: Where to save the image (PNG)
        title: Chart title
        width: Image width in pixels
        height: Image height in pixels
        bar_color: Bar fill color as RGB tuple
        bg_color: Background color as RGB tuple

    Returns:
        Path to the saved image file.
    """
    _ensure_pillow()

    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    title_font = _get_font(28)
    label_font = _get_font(18)
    value_font = _get_font(16)

    # Draw title
    draw.text((20, 15), title, font=title_font, fill=(30, 30, 80))

    if not data:
        draw.text((20, 80), "No data provided.", font=label_font, fill=(100, 100, 100))
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(output_path), "PNG")
        return str(output_path)

    # Chart area
    chart_top = 70
    chart_bottom = height - 60
    chart_left = 180
    chart_right = width - 40
    chart_height = chart_bottom - chart_top
    chart_width = chart_right - chart_left

    # Find max value
    max_val = max(data.values()) if data.values() else 1
    if max_val == 0:
        max_val = 1

    bar_count = len(data)
    bar_spacing = 10
    bar_height = max(10, (chart_height - bar_spacing * (bar_count + 1)) // bar_count)

    # Draw horizontal bars
    y = chart_top + bar_spacing
    for label, value in data.items():
        bar_width = int((value / max_val) * chart_width)

        # Draw label
        label_text = str(label)[:20]  # Truncate long labels
        draw.text((10, y + bar_height // 4), label_text, font=label_font, fill=(50, 50, 80))

        # Draw bar background
        draw.rectangle(
            [(chart_left, y), (chart_right, y + bar_height)],
            fill=(210, 215, 230),
            outline=(180, 185, 210),
        )

        # Draw bar fill
        if bar_width > 0:
            draw.rectangle(
                [(chart_left, y), (chart_left + bar_width, y + bar_height)],
                fill=bar_color,
            )

        # Draw value label
        value_text = f"{value:,.1f}" if isinstance(value, float) else str(value)
        draw.text(
            (chart_left + bar_width + 5, y + bar_height // 4),
            value_text,
            font=value_font,
            fill=(50, 50, 80),
        )

        y += bar_height + bar_spacing

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "PNG")
    return str(output_path)


def generate_banner(
    text: str,
    output_path: str,
    width: int = 800,
    height: int = 200,
    bg_color: tuple = (20, 80, 140),
    text_color: tuple = (255, 255, 255),
    font_size: int = 48,
    subtitle: Optional[str] = None,
) -> str:
    """Generate a simple banner image with centered text.

    Args:
        text: Main banner text
        output_path: Where to save the image (PNG)
        width: Image width in pixels
        height: Image height in pixels
        bg_color: Background color as RGB tuple (default blue)
        text_color: Text color as RGB tuple (default white)
        font_size: Font size for main text
        subtitle: Optional smaller text below the main text

    Returns:
        Path to the saved image file.
    """
    _ensure_pillow()

    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Subtle gradient effect using rectangles
    for i in range(height // 2):
        alpha = int(30 * (1 - i / (height / 2)))
        shade = tuple(min(255, c + alpha) for c in bg_color)
        draw.line([(0, i), (width, i)], fill=shade)

    main_font = _get_font(font_size)

    # Center main text
    bbox = draw.textbbox((0, 0), text, font=main_font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    if subtitle:
        sub_font = _get_font(font_size // 2)
        sub_bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
        sub_height = sub_bbox[3] - sub_bbox[1]
        total_height = text_height + 10 + sub_height
        text_y = (height - total_height) // 2
        sub_y = text_y + text_height + 10

        draw.text(((width - text_width) // 2, text_y), text, font=main_font, fill=text_color)

        sub_width = sub_bbox[2] - sub_bbox[0]
        draw.text(
            ((width - sub_width) // 2, sub_y),
            subtitle,
            font=sub_font,
            fill=tuple(min(255, c + 60) for c in text_color),
        )
    else:
        text_y = (height - text_height) // 2
        draw.text(((width - text_width) // 2, text_y), text, font=main_font, fill=text_color)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "PNG")
    return str(output_path)


if __name__ == "__main__":
    # Quick test
    import tempfile
    import os

    print("Testing image generation...")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Test 1: text image
        p1 = generate_text_image(
            text="Hello from Iris!\nThis is a test of the image generation system.",
            output_path=os.path.join(tmpdir, "test_text.png"),
            title="Test Image",
        )
        print(f"Text image: {p1} ({os.path.getsize(p1)} bytes)")

        # Test 2: bar chart
        p2 = generate_bar_chart(
            data={"Emails Sent": 42, "Emails Received": 17, "Attachments": 5},
            output_path=os.path.join(tmpdir, "test_chart.png"),
            title="Email Statistics",
        )
        print(f"Bar chart: {p2} ({os.path.getsize(p2)} bytes)")

        # Test 3: banner
        p3 = generate_banner(
            text="Iris Mail System",
            output_path=os.path.join(tmpdir, "test_banner.png"),
            subtitle="Attachment Support Active",
        )
        print(f"Banner: {p3} ({os.path.getsize(p3)} bytes)")

    print("All tests passed!")
