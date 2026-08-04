"""Generación de identificaciones QR imprimibles."""

import io

import qrcode
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def build_qr_card_pdf(person, church) -> io.BytesIO:
    """Crea un PDF tamaño carta con un carnet QR listo para recortar."""
    qr_stream = io.BytesIO()
    qrcode.make(person.qr_token).save(qr_stream, format="PNG")
    qr_stream.seek(0)

    output = io.BytesIO()
    page_width, page_height = letter
    card_width, card_height = 270, 430
    x = (page_width - card_width) / 2
    y = (page_height - card_height) / 2
    pdf = canvas.Canvas(output, pagesize=letter)
    pdf.setTitle(f"Carnet QR {person.codigo}")
    pdf.setStrokeColor(HexColor("#3157D5"))
    pdf.setLineWidth(2)
    pdf.roundRect(x, y, card_width, card_height, 14, stroke=1, fill=0)
    pdf.setFillColor(HexColor("#3157D5"))
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawCentredString(page_width / 2, y + card_height - 42, "RMS")
    pdf.setFillColor(HexColor("#172033"))
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawCentredString(page_width / 2, y + card_height - 68, church.nombre[:38])
    pdf.drawImage(ImageReader(qr_stream), x + 45, y + 125, 180, 180)
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawCentredString(
        page_width / 2, y + 95, f"{person.nombres} {person.apellidos}"[:34]
    )
    pdf.setFont("Helvetica", 13)
    pdf.drawCentredString(page_width / 2, y + 70, person.codigo)
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(HexColor("#667085"))
    pdf.drawCentredString(page_width / 2, y + 35, "Identificación personal · No transferible")
    pdf.showPage()
    pdf.save()
    output.seek(0)
    return output
