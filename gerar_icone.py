"""Gera icon.ico — pardal em voo (vista frontal, asas abertas) segurando banner 'DC'."""
from PIL import Image, ImageDraw, ImageFont
import os, struct
from io import BytesIO

SIZES = [256, 128, 64, 48, 32, 16]

GOLD      = (232, 160, 32, 255)
GOLD_DARK = (184, 122, 16, 255)
GOLD_DIM  = (120,  85,  8, 200)
BG        = ( 13,  17, 26, 255)
BANNER_BG = ( 26,  22, 10, 248)
WHITE     = (230, 237, 243, 255)
DARK      = ( 13,  17, 26, 255)


def _font(size):
    for name in ("arialbd", "arial", "calibrib", "calibri"):
        path = f"C:/Windows/Fonts/{name}.ttf"
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _centered_text(d, text, font, cx, cy, fill):
    bb = d.textbbox((0, 0), text, font=font)
    x = cx - (bb[2] - bb[0]) // 2 - bb[0]
    y = cy - (bb[3] - bb[1]) // 2 - bb[1]
    d.text((x, y), text, fill=fill, font=font)


def _sc(v, s):
    """Escala um valor de coordenada (base 256px)."""
    return int(v * s)


def _poly(d, pts, fill, s):
    d.polygon([(_sc(x, s), _sc(y, s)) for x, y in pts], fill=fill)


def _ellipse(d, x0, y0, x1, y1, fill, s):
    d.ellipse([_sc(x0, s), _sc(y0, s), _sc(x1, s), _sc(y1, s)], fill=fill)


def _draw_bird(d, s):
    """
    Pardal em voo — vista ligeiramente de frente/baixo, asas abertas.
    Patas visíveis embaixo do corpo para "segurar" o banner.
    Base: 256x256. Bird ocupa ~y=28..140 na escala base.
    """
    cx, cy = 128, 90   # centro do corpo

    # ── Asas ──────────────────────────────────────────────────────
    # Asa esquerda (vai para cima-esquerda)
    _poly(d, [
        (cx,    cy-8),
        (cx-40, cy-32),
        (cx-78, cy-42),
        (cx-110,cy-26),
        (cx-76, cy-10),
        (cx-30, cy-4),
    ], GOLD, s)

    # Ponta da asa esquerda (detalhe mais escuro)
    _poly(d, [
        (cx-78, cy-42),
        (cx-110,cy-26),
        (cx-98, cy-36),
    ], GOLD_DIM, s)

    # Asa direita (vai para cima-direita)
    _poly(d, [
        (cx,    cy-8),
        (cx+40, cy-32),
        (cx+78, cy-42),
        (cx+110,cy-26),
        (cx+76, cy-10),
        (cx+30, cy-4),
    ], GOLD, s)

    # Ponta da asa direita
    _poly(d, [
        (cx+78, cy-42),
        (cx+110,cy-26),
        (cx+98, cy-36),
    ], GOLD_DIM, s)

    # ── Corpo ──────────────────────────────────────────────────────
    _ellipse(d, cx-20, cy-12, cx+20, cy+16, GOLD, s)

    # ── Cabeça ─────────────────────────────────────────────────────
    _ellipse(d, cx-15, cy-40, cx+15, cy-12, GOLD, s)

    # Bico (pequeno triângulo no topo)
    _poly(d, [
        (cx-4, cy-38),
        (cx,   cy-52),
        (cx+4, cy-38),
    ], GOLD_DARK, s)

    # Olho
    _ellipse(d, cx-6,  cy-34, cx+1,  cy-27, WHITE, s)
    _ellipse(d, cx-5,  cy-33, cx,    cy-28, DARK,  s)
    _ellipse(d, cx+1,  cy-34, cx+8,  cy-27, WHITE, s)
    _ellipse(d, cx+1,  cy-33, cx+6,  cy-28, DARK,  s)

    # ── Cauda ──────────────────────────────────────────────────────
    _poly(d, [
        (cx-14, cy+14),
        (cx-22, cy+40),
        (cx-8,  cy+34),
        (cx,    cy+42),
        (cx+8,  cy+34),
        (cx+22, cy+40),
        (cx+14, cy+14),
    ], GOLD, s)

    # ── Patas (seguram o banner) ────────────────────────────────────
    # Pata esquerda
    _poly(d, [
        (cx-10, cy+16),
        (cx-14, cy+44),
        (cx-8,  cy+44),
        (cx-4,  cy+16),
    ], GOLD_DARK, s)
    # Garras esquerda
    _poly(d, [
        (cx-14, cy+44),
        (cx-20, cy+52),
        (cx-8,  cy+48),
        (cx-6,  cy+44),
    ], GOLD_DARK, s)

    # Pata direita
    _poly(d, [
        (cx+10, cy+16),
        (cx+14, cy+44),
        (cx+8,  cy+44),
        (cx+4,  cy+16),
    ], GOLD_DARK, s)
    # Garras direita
    _poly(d, [
        (cx+14, cy+44),
        (cx+20, cy+52),
        (cx+8,  cy+48),
        (cx+6,  cy+44),
    ], GOLD_DARK, s)


def make_frame(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    s   = size / 256.0

    # ── Fundo ──────────────────────────────────────────────────────
    pad = max(1, size // 12)
    d.rounded_rectangle(
        [pad, pad, size - pad - 1, size - pad - 1],
        radius=size // 4,
        fill=BG,
        outline=GOLD_DARK,
        width=max(1, size // 28),
    )

    # ── Tamanhos muito pequenos: só "DC" ───────────────────────────
    if size <= 20:
        f = _font(int(size * 0.52))
        _centered_text(d, "DC", f, size // 2, size // 2, GOLD)
        return img

    # ── 32-48px: bird simplificado + "DC" ─────────────────────────
    if size <= 48:
        _draw_bird(d, s * 0.72)
        # Reposiciona o "DC" abaixo do pássaro comprimido
        f = _font(max(8, int(size * 0.30)))
        by = int(size * 0.78)
        _centered_text(d, "DC", f, size // 2, by, GOLD)
        return img

    # ── 64px+: pássaro completo + fios + banner DC ─────────────────

    # Pássaro desenhado (ocupa ~y=28..140 na escala de 256px)
    _draw_bird(d, s)

    # ── Fios conectando as patas ao banner ──────────────────────────
    cx  = size // 2
    # Pata esq: aprox (cx-14*s, cy+44*s) = (cx-14s, (90+44)*s) = (cx-14s, 134s)
    # Pata dir: aprox (cx+14*s, 134s)
    foot_y  = _sc(134, s)
    foot_lx = _sc(128 - 14, s)
    foot_rx = _sc(128 + 14, s)

    # Topo do banner
    ban_pad = int(size * 0.04)
    bx0 = _sc(60,  s)
    bx1 = _sc(196, s)
    by0 = _sc(158, s)
    by1 = _sc(228, s)

    rope_w = max(1, int(1.8 * s))
    d.line([(foot_lx, foot_y), (bx0 + int(16*s), by0)], fill=GOLD_DIM, width=rope_w)
    d.line([(foot_rx, foot_y), (bx1 - int(16*s), by0)], fill=GOLD_DIM, width=rope_w)

    # ── Banner / scroll ─────────────────────────────────────────────
    radius = int(10 * s)

    # Sombra
    d.rounded_rectangle(
        [bx0 + int(3*s), by0 + int(3*s), bx1 + int(3*s), by1 + int(3*s)],
        radius=radius, fill=(0, 0, 0, 110),
    )
    # Corpo do banner
    d.rounded_rectangle(
        [bx0, by0, bx1, by1],
        radius=radius,
        fill=BANNER_BG,
        outline=GOLD_DARK,
        width=max(1, int(2.5 * s)),
    )
    # Detalhes laterais do scroll (rollends)
    roll = int(12 * s)
    d.rounded_rectangle([bx0, by0, bx0 + roll, by1],
                         radius=int(7*s), fill=(35, 28, 8, 245), outline=GOLD_DIM,
                         width=max(1, int(1.5*s)))
    d.rounded_rectangle([bx1 - roll, by0, bx1, by1],
                         radius=int(7*s), fill=(35, 28, 8, 245), outline=GOLD_DIM,
                         width=max(1, int(1.5*s)))

    # "DC" no banner
    dc_size = max(8, int((by1 - by0) * 0.65))
    f = _font(dc_size)
    bcx = (bx0 + bx1) // 2
    bcy = (by0 + by1) // 2
    _centered_text(d, "DC", f, bcx, bcy, GOLD)

    return img


def save_ico(frames, path):
    images_data = []
    for img in frames:
        buf = BytesIO()
        img.save(buf, format="PNG")
        images_data.append(buf.getvalue())

    n = len(images_data)
    header = struct.pack("<HHH", 0, 1, n)
    offset = 6 + n * 16
    entries = b""
    for img, data in zip(frames, images_data):
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
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
    save_ico(frames, out)
    print(f"Ícone salvo em: {out}")
