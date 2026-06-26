import io
import os
import qrcode
from qrcode.image.pil import PilImage
from fpdf import FPDF

_BUNDLED_FONT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", "fonts"))


def _bundled(name: str) -> str | None:
    p = os.path.join(_BUNDLED_FONT_DIR, name)
    return p if os.path.isfile(p) else None


def generate_qr_bytes(data: str, size: int = 200) -> bytes:
    img = qrcode.make(data, image_factory=PilImage)
    img = img.resize((size, size))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_ticket_pdf(
    movie_title: str,
    date_str: str,
    time_str: str,
    hall: str,
    seat_row: int,
    seat_col: int,
    price: float,
    qr_token: str,
    is_paid: bool = True,
    phone: str | None = None,
    email: str | None = None,
) -> bytes:
    font_regular = _bundled("NotoSans-Regular.ttf")
    font_bold = _bundled("NotoSans-Bold.ttf")

    if not font_regular:
        font_regular = _bundled("Arial.ttf")
        font_bold = _bundled("Arial-Bold.ttf") or _bundled("arialbd.ttf")

    qr_img = qrcode.make(qr_token, image_factory=PilImage)
    qr_img = qr_img.resize((300, 300))
    tmp_qr = os.path.join(
        os.environ.get("TEMP", os.environ.get("TMPDIR", "/tmp")),
        f"starmin_qr_{os.getpid()}.png",
    )
    qr_img.save(tmp_qr, format="PNG")

    pdf = FPDF(orientation="P", unit="mm", format=(105, 148))
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()

    if font_regular:
        pdf.add_font("Uni", "", font_regular, uni=True)
        if font_bold:
            pdf.add_font("Uni", "B", font_bold, uni=True)
        fn = "Uni"
    else:
        fn = "Helvetica"

    pdf.set_font(fn, "B", 16)
    pdf.cell(0, 12, "StarMIN Cinema", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)

    pdf.set_font(fn, "B", 12)
    pdf.cell(0, 8, movie_title[:35], new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)

    pdf.set_font(fn, "", 10)
    rows = [
        ("Дата", date_str),
        ("Время", time_str),
        ("Зал", hall),
        ("Место", f"Ряд {seat_row}, Место {seat_col}"),
        ("Цена", f"{int(price)} RUB"),
        ("Статус", "ОПЛАЧЕНО" if is_paid else "НЕ ОПЛАЧЕНО"),
    ]
    if phone:
        rows.append(("Телефон", phone))
    if email:
        rows.append(("Email", email))

    for label, val in rows:
        pdf.cell(35, 6, label + ":", align="L")
        pdf.cell(0, 6, val, new_x="LMARGIN", new_y="NEXT", align="R")

    pdf.ln(4)
    qr_x = (pdf.w - 50) / 2
    pdf.image(tmp_qr, x=qr_x, w=50, h=50)

    try:
        os.remove(tmp_qr)
    except OSError:
        pass

    return bytes(pdf.output())
