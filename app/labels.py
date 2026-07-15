from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# PILLOW_ANTIALIAS_COMPAT: Pillow 10 removed RESAMPLE_FILTER, but brother_ql still references it.
try:
    from PIL import Image as _PIL_Image
    if not hasattr(_PIL_Image, "ANTIALIAS"):
        _PIL_RESAMPLE_FILTER = _PIL_Image.Resampling.LANCZOS
except Exception:
    pass


try:
    RESAMPLE_FILTER = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLE_FILTER = Image.LANCZOS

import qrcode

# Compact 62mm continuous label canvas. Lower height = less paper used.
W, H = 300, 300


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



W = 696

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


def row_get(row, key, default=None):
    try:
        value = row[key]
        return default if value is None else value
    except Exception:
        return default


def fmt_dt(value):
    if not value or value == "INFINITE":
        return "NO EXPIRATION"
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%-m/%-d %-I:%M %p")
    except Exception:
        return str(value)


def code128_b_values(data):
    vals = [104]
    checksum = 104
    for idx, ch in enumerate(str(data or ""), start=1):
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


def measure(draw, text, font):
    try:
        box = draw.textbbox((0, 0), str(text), font=font)
        return box[2] - box[0], box[3] - box[1]
    except Exception:
        return len(str(text)) * 10, 20


def fit_text(draw, text, xy, max_width, font, fill=0):
    text = str(text or "")
    if measure(draw, text, font)[0] <= max_width:
        draw.text(xy, text, font=font, fill=fill)
        return
    ell = "..."
    while text and measure(draw, text + ell, font)[0] > max_width:
        text = text[:-1]
    draw.text(xy, text + ell, font=font, fill=fill)


def wrap_text(draw, text, font, max_width, max_lines=2):
    words = str(text or "").split()
    lines = []
    current = ""
    for word in words:
        candidate = word if not current else current + " " + word
        if measure(draw, candidate, font)[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
            if len(lines) >= max_lines:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    if not lines:
        lines = [str(text or "")]
    # Fit long tokens.
    fitted = []
    for line in lines[:max_lines]:
        if measure(draw, line, font)[0] <= max_width:
            fitted.append(line)
        else:
            ell = "..."
            while line and measure(draw, line + ell, font)[0] > max_width:
                line = line[:-1]
            fitted.append(line + ell)
    return fitted


def normalize_sku_for_print(value):
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def label_lines_for_batch(batch):
    lines = [
        f"Batch: {row_get(batch, 'batch_code', '')}",
        f"Made: {fmt_dt(row_get(batch, 'made_at'))} by {row_get(batch, 'made_by', '')}",
        row_get(batch, "storage", ""),
    ]
    allergens = row_get(batch, "allergens", "")
    if allergens:
        lines.append(f"Allergens: {allergens}")
    return [str(x) for x in lines if str(x or "").strip()]


def label_lines_for_service(service):
    if row_get(service, "batch_code"):
        lines = [
            f"Batch: {row_get(service, 'batch_code', '')}",
            f"Bottled: {fmt_dt(row_get(service, 'bottled_at'))} by {row_get(service, 'bottled_by', '')}",
            row_get(service, "storage", ""),
        ]
    else:
        lines = [
            f"Prepped: {fmt_dt(row_get(service, 'bottled_at'))} by {row_get(service, 'bottled_by', '')}",
            row_get(service, "storage", ""),
        ]
    allergens = row_get(service, "allergens", "")
    if allergens:
        lines.append(f"Allergens: {allergens}")
    return [str(x) for x in lines if str(x or "").strip()]


def calculate_label_height(title_lines, detail_lines, has_sku):
    h = 10
    h += len(title_lines) * 35
    h += 8
    h += 25
    h += 38
    h += len(detail_lines) * 21
    h += 8
    if has_sku:
        h += 50
    h += 8
    return max(228, min(h, 326))


def draw_sku_footer(draw, sku, footer_top, height):
    sku = normalize_sku_for_print(sku)
    if not sku:
        return
    draw.line((4, footer_top, W - 5, footer_top), fill=0, width=1)
    barcode_w = 270
    barcode_h = 23
    barcode_x = (W - barcode_w) // 2
    barcode_y = footer_top + 7
    draw_code128(draw, sku, barcode_x, barcode_y, barcode_w, barcode_h)
    sku_w = measure(draw, sku, F_SMALL)[0]
    draw.text(((W - sku_w) // 2, barcode_y + barcode_h + 1), sku, font=F_SMALL, fill=0)


def render_core_label(item_name, label_type, use_by, detail_lines, url, sku, qr_caption):
    sku = normalize_sku_for_print(sku)
    qr_size = 82
    qr_x = W - qr_size - 16
    qr_y = 14
    left = 18

    tmp = Image.new("1", (W, 300), 1)
    tdraw = ImageDraw.Draw(tmp)
    title_max = qr_x - left - 10
    title_lines = wrap_text(tdraw, str(item_name or "ITEM").upper(), F_TITLE, title_max, 2)

    height = calculate_label_height(title_lines, detail_lines, bool(sku))
    footer_top = height - 50 if sku else height - 8

    img = Image.new("1", (W, height), 1)
    draw = ImageDraw.Draw(img)
    draw.rectangle((3, 3, W - 4, height - 4), outline=0, width=2)

    qr = make_qr(url).resize((qr_size, qr_size), RESAMPLE_FILTER)
    img.paste(qr, (qr_x, qr_y))

    y = 10
    for line in title_lines:
        fit_text(draw, line, (left, y), title_max, F_TITLE)
        y += 35

    y += 6
    side_max = title_max if y < qr_y + qr_size + 28 else W - 36
    fit_text(draw, label_type, (left, y), side_max, F_MED)
    y += 27

    side_max = title_max if y < qr_y + qr_size + 28 else W - 36
    fit_text(draw, f"USE BY: {use_by}", (left, y), side_max, F_EXPIRE)
    y += 38

    draw.text((qr_x + 7, qr_y + qr_size + 3), "SCAN", font=F_SMALL, fill=0)
    draw.text((qr_x + 7, qr_y + qr_size + 20), qr_caption, font=F_SMALL, fill=0)

    # Body details start below QR and always use full width.
    y = max(y, qr_y + qr_size + 38)
    for line in detail_lines:
        if y + 19 > footer_top - 3:
            break
        fit_text(draw, line, (left, y), W - 36, F_BODY)
        y += 21

    if sku:
        draw_sku_footer(draw, sku, footer_top, height)

    return img


def render_batch_label(batch, url):
    return render_core_label(
        item_name=row_get(batch, "item_name", "ITEM"),
        label_type="MASTER BATCH",
        use_by=fmt_dt(row_get(batch, "expires_at")),
        detail_lines=label_lines_for_batch(batch),
        url=url,
        sku=row_get(batch, "item_sku", row_get(batch, "sku", "")),
        qr_caption="BATCH",
    )


def render_service_label(service, url):
    is_from_batch = bool(row_get(service, "batch_code"))
    return render_core_label(
        item_name=row_get(service, "item_name", "ITEM"),
        label_type="IN USE" if is_from_batch else "DAY OF PREP",
        use_by=fmt_dt(row_get(service, "expires_at")),
        detail_lines=label_lines_for_service(service),
        url=url,
        sku=row_get(service, "item_sku", row_get(service, "sku", "")),
        qr_caption="LABEL",
    )


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
