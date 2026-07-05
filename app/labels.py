from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# PILLOW_ANTIALIAS_COMPAT: Pillow 10 removed Image.ANTIALIAS, but brother_ql still references it.
try:
    from PIL import Image as _PIL_Image
    if not hasattr(_PIL_Image, "ANTIALIAS"):
        _PIL_Image.ANTIALIAS = _PIL_Image.Resampling.LANCZOS
except Exception:
    pass


try:
    RESAMPLE_FILTER = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLE_FILTER = Image.LANCZOS

import qrcode

# Compact 62mm continuous label canvas. Lower height = less paper used.
W, H = 420, 300


def font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


F_TITLE = font(34, True)
F_EXPIRE = font(34, True)
F_MED = font(22, True)
F_BODY = font(20)
F_SMALL = font(16)


def row_get(row, key, default=None):
    try:
        value = row[key]
        return default if value is None else value
    except Exception:
        return default



CODE128_PATTERNS = [
"212222","222122","222221","121223","121322","131222","122213","122312","132212","221213",
"221312","231212","112232","122132","122231","113222","123122","123221","223211","221132",
"221231","213212","223112","312131","311222","321122","321221","312212","322112","322211",
"212123","212321","232121","111323","131123","131321","112313","132113","132311","211313",
"231113","231311","112133","112331","132131","113123","113321","133121","313121","211331",
"231131","213113","213311","213131","311123","311321","331121","312113","312311","332111",
"314111","221411","431111","111224","111422","121124","121421","141122","141221","112214",
"112412","122114","122411","142112","142211","241211","221114","413111","241112","134111",
"111242","121142","121241","114212","124112","124211","411212","421112","421211","212141",
"214121","412121","111143","111341","131141","114113","114311","411113","411311","113141",
"114131","311141","411131","211412","211214","211232","2331112"
]

def code128_b_values(data):
    data = str(data or "")
    vals = [104]
    checksum = 104
    for idx, ch in enumerate(data, start=1):
        o = ord(ch)
        if o < 32 or o > 126:
            o = ord("?")
        val = o - 32
        vals.append(val)
        checksum += val * idx
    vals.append(checksum % 103)
    vals.append(106)
    return vals

def draw_code128(draw, data, x, y, width, height):
    data = str(data or "")
    if not data:
        return
    vals = code128_b_values(data)
    modules = sum(sum(int(n) for n in CODE128_PATTERNS[v]) for v in vals)
    module_w = max(1, int(width / modules))
    actual_w = modules * module_w
    pos = x + max(0, (width - actual_w) // 2)
    for v in vals:
        bar = True
        for n in CODE128_PATTERNS[v]:
            w = int(n) * module_w
            if bar:
                draw.rectangle((pos, y, pos + w - 1, y + height), fill=0)
            pos += w
            bar = not bar

def draw_sku_barcode(draw, sku, y):
    sku = "".join(ch for ch in str(sku or "") if ch.isdigit())
    if not sku:
        return
    # Dedicated final-line SKU zone, separated from utility label content.
    draw.line((0, y - 10, W, y - 10), fill=0, width=2)
    draw_code128(draw, sku, 145, y + 2, W - 290, 46)
    try:
        bbox = draw.textbbox((0, 0), sku, font=F_SMALL)
        tw = bbox[2] - bbox[0]
    except Exception:
        tw = len(sku) * 10
    draw.text(((W - tw) // 2, y + 51), sku, font=F_SMALL, fill=0)


def fmt_dt(value):
    if not value or value == "INFINITE":
        return "NO EXPIRATION"
    dt = datetime.fromisoformat(value)
    return dt.strftime("%m/%d %I:%M %p").lstrip("0").replace(" 0", " ")


def draw_wrapped(draw, text, xy, max_width, font_obj, fill=0, line_gap=2, max_lines=2):
    x, y = xy
    words = str(text).split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        if draw.textbbox((0, 0), test, font=font_obj)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    for line in lines[:max_lines]:
        draw.text((x, y), line, font=font_obj, fill=fill)
        y += font_obj.size + line_gap
    return y


def make_qr(url):
    qr = qrcode.QRCode(version=None, box_size=4, border=1)
    qr.add_data(url)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("1").resize((104, 104))


def base_canvas(height=H):
    img = Image.new("1", (W, height), 1)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, W - 1, height - 1), outline=0, width=2)
    return img, draw


def render_batch_label(batch, url):
    img, draw = base_canvas()
    qr = make_qr(url)
    img.paste(qr, (574, 14))

    draw_wrapped(draw, row_get(batch, "item_name", "ITEM").upper(), (16, 12), 535, F_TITLE, max_lines=1)

    y = 86
    draw.text((16, y), "MASTER BATCH", font=F_MED, fill=0); y += 36
    draw.text((16, y), f"USE BY: {fmt_dt(row_get(batch, 'expires_at'))}", font=F_EXPIRE, fill=0); y += 50

    draw.text((16, y), f"Batch: {row_get(batch, 'batch_code', '')}", font=F_BODY, fill=0); y += 25
    draw.text((16, y), f"Made: {fmt_dt(row_get(batch, 'made_at'))} by {row_get(batch, 'made_by', '')}", font=F_BODY, fill=0); y += 25
    draw.text((16, y), row_get(batch, "storage", ""), font=F_BODY, fill=0); y += 25

    allergens = row_get(batch, "allergens", "")
    if allergens:
        draw.text((16, y), f"Allergens: {allergens}", font=F_BODY, fill=0)

    draw.text((580, 126), "SCAN", font=F_SMALL, fill=0)
    draw.text((580, 146), "BATCH", font=F_SMALL, fill=0)

    draw_sku_barcode(draw, row_get(batch, "item_sku", row_get(batch, "sku", "")), H - 84)
    return img




def render_service_label(service, url):
    img, draw = base_canvas()
    qr = make_qr(url)
    img.paste(qr, (574, 14))

    draw_wrapped(draw, row_get(service, "item_name", "ITEM").upper(), (16, 12), 535, F_TITLE, max_lines=1)

    y = 86
    label_type = "IN USE" if row_get(service, "batch_code") else "DAY OF PREP"
    draw.text((16, y), label_type, font=F_MED, fill=0); y += 36
    draw.text((16, y), f"USE BY: {fmt_dt(row_get(service, 'expires_at'))}", font=F_EXPIRE, fill=0); y += 50

    if row_get(service, "batch_code"):
        draw.text((16, y), f"Batch: {row_get(service, 'batch_code', '')}", font=F_BODY, fill=0); y += 25
        if row_get(service, "made_at"):
            draw.text((16, y), f"Made: {fmt_dt(row_get(service, 'made_at'))} by {row_get(service, 'made_by', '')}", font=F_BODY, fill=0); y += 25
        draw.text((16, y), f"Bottled: {fmt_dt(row_get(service, 'bottled_at'))} by {row_get(service, 'bottled_by', '')}", font=F_BODY, fill=0); y += 25
    else:
        draw.text((16, y), f"Prepped: {fmt_dt(row_get(service, 'bottled_at'))} by {row_get(service, 'bottled_by', '')}", font=F_BODY, fill=0); y += 25

    draw.text((16, y), row_get(service, "storage", ""), font=F_BODY, fill=0); y += 25

    allergens = row_get(service, "allergens", "")
    if allergens:
        draw.text((16, y), f"Allergens: {allergens}", font=F_BODY, fill=0)

    draw.text((580, 126), "SCAN", font=F_SMALL, fill=0)
    draw.text((580, 146), "LABEL", font=F_SMALL, fill=0)

    draw_sku_barcode(draw, row_get(service, "item_sku", row_get(service, "sku", "")), H - 84)
    return img




def render_custom_label(title, large_text='', small_text='', icon='', footer=''):
    height = 260
    img, draw = base_canvas(height)
    x = 18
    if icon:
        draw.text((18, 18), icon[:3], font=F_TITLE, fill=0)
        x = 95
    draw_wrapped(draw, (title or 'CUSTOM LABEL').upper(), (x, 18), W - x - 24, F_TITLE, max_lines=2)
    y = 94
    if large_text:
        y = draw_wrapped(draw, large_text.upper(), (18, y), W - 36, F_EXPIRE, max_lines=2) + 8
    if small_text:
        y = draw_wrapped(draw, small_text, (18, y), W - 36, F_BODY, max_lines=3) + 8
    if footer:
        draw.text((18, height - 32), footer, font=F_SMALL, fill=0)
    return img
