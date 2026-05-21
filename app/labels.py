from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import qrcode


W, H = 696, 420  # 62mm continuous label width at Brother QL print width; compact food label height.


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


F_TITLE = font(46, True)
F_BIG = font(38, True)
F_MED = font(25, True)
F_BODY = font(22)
F_SMALL = font(18)


def fmt_dt(value):
    dt = datetime.fromisoformat(value)
    return dt.strftime("%m/%d %I:%M %p").lstrip("0").replace(" 0", " ")


def draw_wrapped(draw, text, xy, max_width, font_obj, fill=0, line_gap=4, max_lines=2):
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
    qr = qrcode.QRCode(version=None, box_size=5, border=1)
    qr.add_data(url)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("1").resize((130, 130))


def base_canvas():
    img = Image.new("1", (W, H), 1)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, W - 1, H - 1), outline=0, width=3)
    return img, draw


def render_batch_label(batch, url):
    img, draw = base_canvas()
    qr = make_qr(url)
    img.paste(qr, (545, 22))

    draw_wrapped(draw, batch["item_name"].upper(), (24, 20), 500, F_TITLE, max_lines=2)

    draw.text((24, 132), "MASTER BATCH", font=F_MED, fill=0)
    draw.text((24, 172), f"USE BY: {fmt_dt(batch['expires_at'])}", font=F_BIG, fill=0)

    y = 235
    draw.text((24, y), f"Batch: {batch['batch_code']}", font=F_BODY, fill=0); y += 32
    draw.text((24, y), f"Made: {fmt_dt(batch['made_at'])}", font=F_BODY, fill=0); y += 32
    draw.text((24, y), f"By: {batch['made_by']}", font=F_BODY, fill=0); y += 32
    draw.text((24, y), f"{batch['storage']}", font=F_BODY, fill=0); y += 32

    if batch["allergens"]:
        draw.text((24, 374), f"Allergens: {batch['allergens']}", font=F_SMALL, fill=0)

    draw.text((550, 158), "SCAN", font=F_SMALL, fill=0)
    draw.text((550, 178), "BATCH", font=F_SMALL, fill=0)
    return img


def render_service_label(service, url):
    img, draw = base_canvas()
    qr = make_qr(url)
    img.paste(qr, (545, 22))

    draw_wrapped(draw, service["item_name"].upper(), (24, 20), 500, F_TITLE, max_lines=2)

    draw.text((24, 132), "IN USE", font=F_MED, fill=0)
    draw.text((24, 172), f"EXPIRES: {fmt_dt(service['expires_at'])}", font=F_BIG, fill=0)

    y = 235
    draw.text((24, y), f"Service: {service['service_code']}", font=F_BODY, fill=0); y += 31
    draw.text((24, y), f"Batch: {service['batch_code']}", font=F_BODY, fill=0); y += 31
    draw.text((24, y), f"Made: {fmt_dt(service['made_at'])} by {service['made_by']}", font=F_BODY, fill=0); y += 31
    draw.text((24, y), f"Bottled: {fmt_dt(service['bottled_at'])} by {service['bottled_by']}", font=F_BODY, fill=0); y += 31
    draw.text((24, y), f"{service['storage']}", font=F_BODY, fill=0)

    if service["allergens"]:
        draw.text((24, 374), f"Allergens: {service['allergens']}", font=F_SMALL, fill=0)

    draw.text((550, 158), "SCAN", font=F_SMALL, fill=0)
    draw.text((550, 178), "BOTTLE", font=F_SMALL, fill=0)
    return img
