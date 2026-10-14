from datetime import datetime
from pathlib import Path

from services.data_reader import read_data_file
from services.excel_exporter import export_data_with_status
from services.pdf_reader import (
    extract_cod_amount,
    extract_pages,
    find_phone_number,
    normalize_amount,
    normalize_phone,
)
from services.pdf_writer import SERIAL_X, SERIAL_Y, write_serial_numbers
from services.licensing import validate_installed_license


def create_timestamp() -> str:
    """
    Example:

        2026-09-28-08-23-45-PM
    """

    return datetime.now().strftime("%Y-%m-%d-%I-%M-%S-%p")


def find_cod_column(columns) -> str:
    normalized_columns = {
        "".join(
            character.lower() for character in str(column) if character.isalnum()
        ): str(column)
        for column in columns
    }
    exact_matches = [
        ("cods", "cod"),
        ("مبلغالتحصيل",),
    ]

    for aliases in exact_matches:
        matches = [
            original
            for normalized, original in normalized_columns.items()
            if normalized in aliases
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(
                "Multiple COD amount columns found. Keep only one COD column."
            )

    candidates = [
        original
        for normalized, original in normalized_columns.items()
        if "cod" in normalized or "تحصيل" in normalized
    ]
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        raise ValueError("Multiple COD amount columns found. Keep only one COD column.")

    raise ValueError(
        "Missing COD amount column. Use a COD/CODS column or مبلغ التحصيل."
    )


def process_shipment(
    data_file: str,
    policy_pdf: str,
    output_directory: str,
    serial_x: float = SERIAL_X,
    serial_y: float = SERIAL_Y,
):
    """
    Complete shipment processing.

    Creates:

        <data-name>-YYYY-MM-DD-HH-MM-SS-AM/PM.xlsx

        shipment-policy-YYYY-MM-DD-HH-MM-SS-AM/PM.pdf

    The PDF is only created when at least one page matches a known phone
    number. The Excel report is always created.
    """

    validate_installed_license()

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
    cod_column = find_cod_column(df.columns)

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
    page_phones = {}

    matched_phones = set()
    phone_pages = {}
    page_cod_amounts = {}

    unmatched_pages = []

    for page in pages:

        page_number = page["page_number"]

        text = page["text"]
        page_cod_amounts[page_number] = extract_cod_amount(text)

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

        page_phones[page_number] = normalized_phone

        matched_phones.add(normalized_phone)
        phone_pages.setdefault(normalized_phone, []).append(page_number)

    # -------------------------------------------------
    # IMPORTANT:
    # Match DATA rows, not just PDF pages.
    # -------------------------------------------------

    matched_rows = set()
    unmatched_rows = set()
    row_pages = {}
    wrong_cod_rows = set()
    wrong_cod_pages = set()
    row_cod_amounts = {}

    for index, row in df.iterrows():

        phone = normalize_phone(row["phone_number"])

        if phone in matched_phones:

            matched_rows.add(index)
            row_pages[index] = phone_pages[phone]
            shipment_cod = normalize_amount(row[cod_column])
            policy_amounts = [
                page_cod_amounts.get(page_number)
                for page_number in phone_pages[phone]
                if page_cod_amounts.get(page_number) is not None
            ]
            row_cod_amounts[index] = ", ".join(
                format(policy_amount, "f") for policy_amount in policy_amounts
            )
            if shipment_cod is not None and any(
                policy_amount != shipment_cod for policy_amount in policy_amounts
            ):
                wrong_cod_rows.add(index)
                wrong_cod_pages.update(phone_pages[phone])
        else:
            unmatched_rows.add(index)
            row_pages[index] = []

    for page_number, phone in page_phones.items():
        if page_number not in wrong_cod_pages:
            page_serials[page_number] = phone_serials[phone]

    page_order = []
    ordered_pages = set()
    for _, row in df.iterrows():
        phone = normalize_phone(row["phone_number"])
        for page_number in phone_pages.get(phone, []):
            if page_number not in ordered_pages:
                page_order.append(page_number)
                ordered_pages.add(page_number)
    for page_number in range(1, len(pages) + 1):
        if page_number not in ordered_pages:
            page_order.append(page_number)

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
        wrong_cod_rows=wrong_cod_rows,
        cod_column_name=cod_column,
        row_cod_amounts=row_cod_amounts,
        row_pages=row_pages,
        output_file=str(excel_output),
    )

    pdf_output = None

    if page_serials or wrong_cod_pages:

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
            serial_x=serial_x,
            serial_y=serial_y,
            wrong_cod_pages=wrong_cod_pages,
            page_order=page_order,
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
        "wrong_cod_rows": len(wrong_cod_rows),
        "unmatched_rows": len(unmatched_rows),
        "excel_file": str(excel_output),
        "pdf_file": str(pdf_output) if pdf_output else None,
    }
