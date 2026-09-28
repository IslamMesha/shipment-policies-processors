import re

from pypdf import PdfReader


def normalize_phone(phone: str) -> str:
    """
    Normalize an Egyptian phone number.

    Examples:

        01005066374
        201005066374
        +201005066374
        00201005066374
        1005066374

    All become:

        01005066374
    """

    if not phone:
        return ""

    phone = str(phone).strip()

    # Convert Arabic-Indic digits to English digits
    arabic_digits = str.maketrans(
        "٠١٢٣٤٥٦٧٨٩",
        "0123456789",
    )

    phone = phone.translate(arabic_digits)

    # Keep digits only
    phone = re.sub(r"\D", "", phone)

    if not phone:
        return ""

    # 0020xxxxxxxxxx -> 20xxxxxxxxxx
    if phone.startswith("0020"):
        phone = phone[2:]

    # +20 is already removed by the digit cleaning
    # so:
    #
    # 201005066374
    #
    # becomes:
    #
    # 01005066374

    if phone.startswith("20") and len(phone) == 12:
        phone = "0" + phone[2:]

    # If the leading zero was lost in Excel:
    #
    # 1005066374 -> 01005066374
    #
    if len(phone) == 10 and phone.startswith(("10", "11", "12", "15")):
        phone = "0" + phone

    return phone


def extract_pages(pdf_path: str):
    """
    Extract text from every PDF page.
    """

    reader = PdfReader(pdf_path)

    pages = []

    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):
        text = page.extract_text() or ""

        pages.append(
            {
                "page_number": page_number,
                "text": text,
            }
        )

    return pages


def extract_phone_candidates(text: str) -> set[str]:
    """
    Extract possible phone-number candidates from
    PDF text and normalize them.
    """

    candidates = set()

    if not text:
        return candidates

    # Convert Arabic digits first
    arabic_digits = str.maketrans(
        "٠١٢٣٤٥٦٧٨٩",
        "0123456789",
    )

    normalized_text = text.translate(arabic_digits)

    # Find digit sequences
    digit_sequences = re.findall(
        r"\d{10,14}",
        normalized_text,
    )

    for sequence in digit_sequences:

        phone = normalize_phone(sequence)

        if phone.startswith("01") and len(phone) == 11:
            candidates.add(phone)

    return candidates


def find_phone_number(
    text: str,
    phone_numbers: list[str],
):
    """
    Find a phone number from the known data inside
    one PDF page.
    """

    known_phones = {
        normalize_phone(phone): phone
        for phone in phone_numbers
        if normalize_phone(phone)
    }

    page_phones = extract_phone_candidates(text)

    for normalized_phone in page_phones:

        if normalized_phone in known_phones:
            return known_phones[normalized_phone]

    return None
