from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import qrcode

# Compact 62mm continuous label canvas. Lower height = less paper used.
W, H = 696, 300


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


def fmt_dt(value):
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
    img.paste(make_qr(url), (568, 16))

    draw_wrapped(draw, batch["item_name"].upper(), (18, 12), 530, F_TITLE, max_lines=2)
    draw.text((18, 88), "MASTER BATCH", font=F_MED, fill=0)
    draw.text((18, 118), f"USE BY: {fmt_dt(batch['expires_at'])}", font=F_EXPIRE, fill=0)

    y = 166
    draw.text((18, y), f"Batch: {batch['batch_code']}", font=F_BODY, fill=0); y += 26
    draw.text((18, y), f"Made: {fmt_dt(batch['made_at'])} by {batch['made_by']}", font=F_BODY, fill=0); y += 26
    draw.text((18, y), batch["storage"], font=F_BODY, fill=0); y += 26
    if batch["allergens"]:
        draw.text((18, y), f"Allergens: {batch['allergens']}", font=F_BODY, fill=0)

    draw.text((575, 124), "SCAN", font=F_SMALL, fill=0)
    draw.text((575, 144), "BATCH", font=F_SMALL, fill=0)
    return img


def render_service_label(service, url):
    img, draw = base_canvas()
    img.paste(make_qr(url), (568, 16))

    draw_wrapped(draw, service["item_name"].upper(), (18, 12), 530, F_TITLE, max_lines=2)
    draw.text((18, 88), "IN USE", font=F_MED, fill=0)
    draw.text((18, 118), f"EXPIRES: {fmt_dt(service['expires_at'])}", font=F_EXPIRE, fill=0)

    y = 166
    draw.text((18, y), f"Service: {service['service_code']}", font=F_BODY, fill=0); y += 25
    draw.text((18, y), f"Batch: {service['batch_code']}", font=F_BODY, fill=0); y += 25
    draw.text((18, y), f"Made: {fmt_dt(service['made_at'])} by {service['made_by']}", font=F_SMALL, fill=0); y += 22
    draw.text((18, y), f"Bottled: {fmt_dt(service['bottled_at'])} by {service['bottled_by']}", font=F_SMALL, fill=0); y += 22
    draw.text((18, y), service["storage"], font=F_SMALL, fill=0)
    if service["allergens"]:
        draw.text((18, 290), f"Allergens: {service['allergens']}", font=F_SMALL, fill=0)

    draw.text((575, 124), "SCAN", font=F_SMALL, fill=0)
    draw.text((575, 144), "BOTTLE", font=F_SMALL, fill=0)
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
