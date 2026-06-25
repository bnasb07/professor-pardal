"""Gera icon.ico com o logo do Professor Pardal usando Pillow."""
from PIL import Image, ImageDraw, ImageFont
import struct, zlib, os

SIZES = [256, 128, 64, 48, 32, 16]

def make_frame(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)

    # Fundo arredondado dourado-escuro
    pad = max(1, size // 12)
    d.rounded_rectangle(
        [pad, pad, size - pad - 1, size - pad - 1],
        radius=size // 4,
        fill=(26, 27, 34, 255),
        outline=(184, 122, 16, 220),
        width=max(1, size // 28),
    )

    # Emoji 🐦 centralizado — tenta fonte, cai no círculo âmbar
    emoji = "🐦"
    font_size = int(size * 0.52)
    font = None
    for path in [
        "C:/Windows/Fonts/seguiemj.ttf",
        "C:/Windows/Fonts/Segoe UI Emoji.ttf",
    ]:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, font_size)
                break
            except Exception:
                pass

    if font:
        bbox = d.textbbox((0, 0), emoji, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (size - w) // 2 - bbox[0]
        y = (size - h) // 2 - bbox[1]
        d.text((x, y), emoji, font=font, embedded_color=True)
    else:
        # Fallback: círculo âmbar com "P"
        cx, cy, r = size // 2, size // 2, int(size * 0.3)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(232, 160, 32, 255))
        try:
            fb = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", int(size * 0.35))
        except Exception:
            fb = ImageFont.load_default()
        bbox = d.textbbox((0, 0), "P", font=fb)
        d.text(
            (cx - (bbox[2] - bbox[0]) // 2, cy - (bbox[3] - bbox[1]) // 2 - bbox[1]),
            "P", font=fb, fill=(0, 0, 0, 255),
        )

    return img


def save_ico(frames, path):
    """Salva lista de imagens RGBA como .ico multi-tamanho."""
    images_data = []
    for img in frames:
        from io import BytesIO
        buf = BytesIO()
        img.save(buf, format="PNG")
        images_data.append(buf.getvalue())

    # ICO header
    n = len(images_data)
    header = struct.pack("<HHH", 0, 1, n)

    offset = 6 + n * 16
    entries = b""
    for i, (img, data) in enumerate(zip(frames, images_data)):
        w = img.width if img.width < 256 else 0
        h = img.height if img.height < 256 else 0
        entries += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(data), offset)
        offset += len(data)

    with open(path, "wb") as f:
        f.write(header + entries)
        for data in images_data:
            f.write(data)


if __name__ == "__main__":
    print("Gerando icon.ico...")
    frames = [make_frame(s) for s in SIZES]
    out = os.path.join(os.path.dirname(__file__), "icon.ico")
    save_ico(frames, out)
    print(f"Icone salvo em: {out}")
