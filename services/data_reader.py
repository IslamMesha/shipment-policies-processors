import re
from pathlib import Path

import pandas as pd


def _format_timestamp(value: str) -> str:
    value = str(value).strip()

    if not re.search(
        r"\d{1,4}[-/]\d{1,2}[-/]\d{1,4}[ T]\d{1,2}:\d{2}",
        value,
    ):
        return value

    timestamp = pd.to_datetime(value, errors="coerce")

    if pd.isna(timestamp):
        return value

    return timestamp.strftime("%Y-%m-%d %I:%M:%S %p")


def read_data_file(file_path: str) -> pd.DataFrame:
    """
    Read the complete CSV or Excel file.

    The complete dataset is preserved.
    No rows are filtered here.
    """

    path = Path(file_path)

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(
            file_path,
            dtype=str,
            keep_default_na=False,
        )

    elif path.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(
            file_path,
            dtype=str,
        ).fillna("")

    else:
        raise ValueError("Unsupported data file. " "Please select CSV or Excel.")

    # Clean column names
    df.columns = df.columns.astype(str).str.strip()

    required_columns = {
        "phone_number",
        "serial_number",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))

    # Clean values WITHOUT removing any rows
    df["phone_number"] = df["phone_number"].astype(str).str.strip()

    df["serial_number"] = df["serial_number"].astype(str).str.strip()

    # Standardize timestamp cells for the exported workbook.
    for column in df.columns:
        if column not in {"phone_number", "serial_number"}:
            df[column] = df[column].map(_format_timestamp)

    return df
