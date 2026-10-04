from io import BytesIO

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

# Your sample PDF:
# width  = 297.12
# height = 420.00
#
# Serial number position:
# x = 48.56 -> horizontal center
# y = 125    -> large empty area
#
# Font:
# Helvetica-Bold
# 28 pt


SERIAL_X = 48.56
SERIAL_Y = 125
SERIAL_FONT_SIZE = 28


def create_text_overlay(
    page_width: float,
    page_height: float,
    text: str,
    serial_x: float = SERIAL_X,
    serial_y: float = SERIAL_Y,
):
    """
    Create a transparent PDF overlay containing
    the serial number.
    """

    buffer = BytesIO()

    c = canvas.Canvas(
        buffer,
        pagesize=(
            page_width,
            page_height,
        ),
    )

    c.setFont(
        "Helvetica-Bold",
        SERIAL_FONT_SIZE,
    )

    # Center the serial number horizontally
    c.drawCentredString(
        serial_x,
        serial_y,
        str(text),
    )

    c.save()

    buffer.seek(0)

    overlay_reader = PdfReader(buffer)

    return overlay_reader.pages[0]


def write_serial_numbers(
    input_pdf: str,
    output_pdf: str,
    page_serials: dict[int, str],
    serial_x: float = SERIAL_X,
    serial_y: float = SERIAL_Y,
    wrong_cod_pages: set[int] | None = None,
    page_order: list[int] | None = None,
):
    """
    Write serial numbers onto matched PDF pages.

    page_serials example:

        {
            1: "SN001",
            2: "SN002",
            5: "SN005",
        }
    """

    reader = PdfReader(input_pdf)
    writer = PdfWriter()
    wrong_cod_pages = wrong_cod_pages or set()
    page_numbers = page_order or list(range(1, len(reader.pages) + 1))

    for page_number in page_numbers:
        page = reader.pages[page_number - 1]

        label = (
            "wrong CODS"
            if page_number in wrong_cod_pages
            else page_serials.get(page_number)
        )

        if label:

            page_width = float(page.mediabox.width)

            page_height = float(page.mediabox.height)

            overlay = create_text_overlay(
                page_width=page_width,
                page_height=page_height,
                text=label,
                serial_x=serial_x,
                serial_y=serial_y,
            )

            page.merge_page(overlay)

        writer.add_page(page)

    with open(
        output_pdf,
        "wb",
    ) as output_file:

        writer.write(output_file)
