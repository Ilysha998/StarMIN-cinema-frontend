import io
import os
import base64
import qrcode
from qrcode.image.pil import PilImage
from fpdf import FPDF

_FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
_SYSTEM_FONT = "C:\\Windows\\Fonts"


def _find_font(name: str) -> str | None:
    for d in (_FONT_DIR, _SYSTEM_FONT):
        p = os.path.join(d, name)
        if os.path.isfile(p):
            return p
    return None


def generate_qr_bytes(data: str, size: int = 200) -> bytes:
    img = qrcode.make(data, image_factory=PilImage)
    img = img.resize((size, size))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_qr_base64(data: str, size: int = 200) -> str:
    raw = generate_qr_bytes(data, size)
    return base64.b64encode(raw).decode("utf-8")


def generate_ticket_pdf(
    movie_title: str,
    date_str: str,
    time_str: str,
    hall: str,
    seat: int,
    price: float,
    qr_token: str,
    is_paid: bool = True,
    phone: str | None = None,
    email: str | None = None,
) -> bytes:
    arial = _find_font("arial.ttf")
    arial_bd = _find_font("arialbd.ttf")

    qr_img = qrcode.make(qr_token, image_factory=PilImage)
    qr_img = qr_img.resize((300, 300))
    tmp_qr = os.path.join(os.environ.get("TEMP", "/tmp"), f"ticket_qr_{os.getpid()}.png")
    qr_img.save(tmp_qr, format="PNG")

    pdf = FPDF(orientation="P", unit="mm", format=(105, 148))
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()

    if arial:
        pdf.add_font("Arial", "", arial, uni=True)
        if arial_bd:
            pdf.add_font("Arial", "B", arial_bd, uni=True)
        fn = "Arial"
    else:
        fn = "Helvetica"

    pdf.set_font(fn, "B", 16)
    pdf.cell(0, 12, "StarMIN Cinema", ln=True, align="C")
    pdf.ln(4)

    pdf.set_font(fn, "B", 12)
    pdf.cell(0, 8, movie_title[:35], ln=True, align="C")
    pdf.ln(4)

    pdf.set_font(fn, "", 10)
    rows = [
        ("Дата", date_str),
        ("Время", time_str),
        ("Зал", hall),
        ("Место", str(seat)),
        ("Цена", f"{int(price)} ₽"),
        ("Статус", "ОПЛАЧЕНО" if is_paid else "НЕ ОПЛАЧЕНО"),
    ]
    if phone:
        rows.append(("Телефон", phone))
    if email:
        rows.append(("Email", email))

    for label, val in rows:
        pdf.cell(35, 6, label + ":", align="L")
        pdf.cell(0, 6, val, ln=True, align="R")

    pdf.ln(4)
    qr_x = (pdf.w - 50) / 2
    pdf.image(tmp_qr, x=qr_x, w=50, h=50)

    try:
        os.remove(tmp_qr)
    except OSError:
        pass

    return bytes(pdf.output())
