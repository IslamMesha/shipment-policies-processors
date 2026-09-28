from datetime import datetime
from pathlib import Path

from services.data_reader import read_data_file
from services.excel_exporter import export_data_with_status
from services.pdf_reader import extract_pages, find_phone_number, normalize_phone
from services.pdf_writer import write_serial_numbers


def create_timestamp() -> str:
    """
    Example:

        2026-09-28-08-23-PM
    """

    return datetime.now().strftime("%Y-%m-%d-%I-%M-%p")


def process_shipment(
    data_file: str,
    policy_pdf: str,
    output_directory: str,
):
    """
    Complete shipment processing.

    Creates:

        <data-name>-YYYY-MM-DD-HH-MM-AM/PM.xlsx

        shipment-policy-YYYY-MM-DD-HH-MM-AM/PM.pdf
    """

    # -------------------------------------------------
    # Timestamp
    # -------------------------------------------------

    timestamp = create_timestamp()

    # -------------------------------------------------
    # Output directory
    # -------------------------------------------------

    output_dir = Path(output_directory)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -------------------------------------------------
    # Read COMPLETE data file
    # -------------------------------------------------

    df = read_data_file(data_file)

    # -------------------------------------------------
    # Create phone -> serial mapping
    # -------------------------------------------------

    phone_serials = {}

    for _, row in df.iterrows():

        phone = normalize_phone(row["phone_number"])

        serial = str(row["serial_number"]).strip()

        if phone and serial:

            phone_serials[phone] = serial

    if not phone_serials:

        raise ValueError(
            "No valid phone numbers and serial " "numbers were found in the data file."
        )

    # -------------------------------------------------
    # Read policy PDF
    # -------------------------------------------------

    pages = extract_pages(policy_pdf)

    # -------------------------------------------------
    # Match every PDF page
    # -------------------------------------------------

    page_serials = {}

    matched_phones = set()

    unmatched_pages = []

    for page in pages:

        page_number = page["page_number"]

        text = page["text"]

        phone = find_phone_number(
            text,
            list(phone_serials.keys()),
        )

        if phone is None:

            unmatched_pages.append(page_number)

            continue

        normalized_phone = normalize_phone(phone)

        serial = phone_serials.get(normalized_phone)

        if not serial:

            unmatched_pages.append(page_number)

            continue

        # PDF page -> serial number
        page_serials[page_number] = serial

        matched_phones.add(normalized_phone)

    # -------------------------------------------------
    # IMPORTANT:
    # Match DATA rows, not just PDF pages.
    # -------------------------------------------------

    matched_rows = set()
    unmatched_rows = set()

    for index, row in df.iterrows():

        phone = normalize_phone(row["phone_number"])

        if phone in matched_phones:

            matched_rows.add(index)
        else:
            unmatched_rows.add(index)

    # -------------------------------------------------
    # Create Excel filename
    # -------------------------------------------------

    data_name = Path(data_file).stem

    excel_filename = f"{data_name}-{timestamp}.xlsx"

    excel_output = output_dir / excel_filename

    # -------------------------------------------------
    # Export COMPLETE Excel data
    # -------------------------------------------------

    export_data_with_status(
        df=df,
        matched_rows=matched_rows,
        output_file=str(excel_output),
    )

    # -------------------------------------------------
    # Create PDF filename
    # -------------------------------------------------

    pdf_filename = f"shipment-policy-{timestamp}.pdf"

    pdf_output = output_dir / pdf_filename

    # -------------------------------------------------
    # Write serial numbers to PDF
    # -------------------------------------------------

    write_serial_numbers(
        input_pdf=policy_pdf,
        output_pdf=str(pdf_output),
        page_serials=page_serials,
    )

    # -------------------------------------------------
    # Return result
    # -------------------------------------------------

    return {
        "total_data_rows": len(df),
        "total_pages": len(pages),
        "matched_pages": len(page_serials),
        "unmatched_pages": unmatched_pages,
        "matched_rows": len(matched_rows),
        "unmatched_rows": len(unmatched_rows),
        "excel_file": str(excel_output),
        "pdf_file": str(pdf_output),
    }
