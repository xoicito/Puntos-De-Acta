from openpyxl import load_workbook
from openpyxl.styles import Alignment

PROGRAM_PLACEHOLDER = "{{PROGRAMACION}}"


def render_excel(template_path, output_path, replacements):

    wb = load_workbook(template_path)

    rows = replacements.pop(
        "__PROGRAMACION_ROWS__",
        [],
    )

    for ws in wb.worksheets:

        prog_cell = None

        for row in ws.iter_rows():

            for cell in row:

                if cell.value == PROGRAM_PLACEHOLDER:
                    prog_cell = cell

                if isinstance(cell.value, str):

                    for key, value in replacements.items():

                        if (
                            isinstance(value, str)
                            and key in cell.value
                        ):

                            cell.value = cell.value.replace(
                                key,
                                value,
                            )

                            cell.alignment = Alignment(
                                wrap_text=True,
                                vertical="top",
                            )

        if prog_cell:

            row_number = prog_cell.row

            if rows:

                text = "\n".join(
                    [
                        (
                            f"{x['area']} | "
                            f"{x['inicio']} | "
                            f"{x['fin']} | "
                            f"{x['obs']}"
                        )
                        for x in rows
                    ]
                )

            else:

                text = (
                    "Sin programación registrada"
                )

            ws.cell(
                row_number,
                prog_cell.column,
            ).value = text

            ws.cell(
                row_number,
                prog_cell.column,
            ).alignment = Alignment(
                wrap_text=True,
                vertical="top",
            )

            ws.row_dimensions[
                row_number
            ].height = max(
                90,
                18 * (len(rows) + 1),
            )

    wb.save(output_path)

    return output_path
