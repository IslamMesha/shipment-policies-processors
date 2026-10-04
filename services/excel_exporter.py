from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill


def export_data_with_status(
    df: pd.DataFrame,
    matched_rows: set[int],
    wrong_cod_rows: set[int],
    cod_column_name: str,
    row_cod_amounts: dict[int, str],
    row_pages: dict[int, list[int]],
    output_file: str,
):
    """
    Export the COMPLETE original dataset.

    Adds:
        status = Matched
        status = Not found
        page = matched PDF page number(s), or Not found

    Not found rows are highlighted yellow.
    """

    # Never modify the original DataFrame
    result_df = df.copy()

    result_df["page"] = [
        ", ".join(map(str, row_pages.get(row_index, []))) or "Not found"
        for row_index in result_df.index
    ]
    result_df["PDF CODS"] = [
        row_cod_amounts.get(row_index, "")
        for row_index in result_df.index
    ]

    # -------------------------------------------------
    # Add status to EVERY row
    # -------------------------------------------------

    result_df["status"] = "Not found"

    for row_index in matched_rows:

        result_df.loc[row_index, "status"] = "Matched"

    for row_index in wrong_cod_rows:

        result_df.loc[row_index, "status"] = "Wrong CODS"

    # -------------------------------------------------
    # Export the COMPLETE dataset
    # -------------------------------------------------

    output_path = Path(output_file)

    result_df.to_excel(
        output_path,
        index=False,
    )

    # -------------------------------------------------
    # Open Excel
    # -------------------------------------------------

    workbook = load_workbook(output_path)

    worksheet = workbook.active

    # -------------------------------------------------
    # Yellow fill
    # -------------------------------------------------

    yellow_fill = PatternFill(
        fill_type="solid",
        fgColor="FFFF00",
    )

    # -------------------------------------------------
    # Header style
    # -------------------------------------------------

    for cell in worksheet[1]:

        cell.font = Font(bold=True)

        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
        )

    # -------------------------------------------------
    # Highlight Not Found rows
    # -------------------------------------------------

    for row_index in range(len(result_df)):

        if row_index not in matched_rows:

            # DataFrame row 0 -> Excel row 2
            excel_row = row_index + 2

            for cell in worksheet[excel_row]:

                cell.fill = yellow_fill

    cod_column = next(
        (cell.column for cell in worksheet[1] if cell.value == cod_column_name),
        None,
    )
    if cod_column:
        for row_index in wrong_cod_rows:
            worksheet.cell(row=row_index + 2, column=cod_column).fill = yellow_fill

    # -------------------------------------------------
    # Find status column
    # -------------------------------------------------

    status_column = None

    for cell in worksheet[1]:

        if cell.value == "status":

            status_column = cell.column

            break

    # -------------------------------------------------
    # Center status
    # -------------------------------------------------

    if status_column:

        for row in range(
            2,
            worksheet.max_row + 1,
        ):

            worksheet.cell(
                row=row,
                column=status_column,
            ).alignment = Alignment(
                horizontal="center",
                vertical="center",
            )

    # -------------------------------------------------
    # Auto column widths
    # -------------------------------------------------

    for column in worksheet.columns:

        max_length = 0

        column_letter = column[0].column_letter

        for cell in column:

            if cell.value is not None:

                max_length = max(
                    max_length,
                    len(str(cell.value)),
                )

        worksheet.column_dimensions[column_letter].width = min(
            max_length + 2,
            50,
        )

    # -------------------------------------------------
    # Freeze header
    # -------------------------------------------------

    worksheet.freeze_panes = "A2"

    # -------------------------------------------------
    # Save
    # -------------------------------------------------

    workbook.save(output_path)

    return str(output_path)
