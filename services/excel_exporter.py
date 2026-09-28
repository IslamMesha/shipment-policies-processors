from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill


def export_data_with_status(
    df: pd.DataFrame,
    matched_rows: set[int],
    output_file: str,
):
    """
    Export the COMPLETE original dataset.

    Adds:
        status = Matched
        status = Not found

    Not found rows are highlighted yellow.
    """

    # Never modify the original DataFrame
    result_df = df.copy()

    # -------------------------------------------------
    # Add status to EVERY row
    # -------------------------------------------------

    result_df["status"] = "Not found"

    for row_index in matched_rows:

        result_df.loc[row_index, "status"] = "Matched"

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
