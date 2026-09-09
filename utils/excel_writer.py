from openpyxl import load_workbook
from openpyxl.styles import Alignment


def write_lines(ws, start_row, column, text):

    lines = [
        x.strip()
        for x in str(text or "").splitlines()
        if x.strip()
    ]

    for i, line in enumerate(lines):

        ws.cell(
            row=start_row + i,
            column=column
        ).value = line

        ws.cell(
            row=start_row + i,
            column=column
        ).alignment = Alignment(
            wrap_text=True,
            vertical="top"
        )


def write_lines(ws, start_row, column, text):

    lines = [
        x.strip()
        for x in str(text or "").splitlines()
        if x.strip()
    ]

    for offset, line in enumerate(lines):

        ws.cell(
            row=start_row + offset,
            column=column
        ).value = line

        ws.cell(
            row=start_row + offset,
            column=column
        ).alignment = Alignment(
            wrap_text=True,
            vertical="top"
        )

def render_excel(template_path, output_path, replacements):

    wb = load_workbook(template_path)

    for ws in wb.worksheets:

        # PROGRAMACION
        if "{{PROGRAMACION}}" in str(ws["D62"].value):

            ws["D62"] = str(
                replacements.get(
                    "{{PROGRAMACION}}",
                    ""
                )
            )

        # TRABAJOS PREVIOS
        write_lines(
            ws,
            69,
            5,
            replacements.get(
                "{{TRABAJOS_PREVIOS}}",
                ""
            )
        )

        # SERVICIOS BASICOS
        write_lines(
            ws,
            76,
            5,
            replacements.get(
                "{{SERVICIOS_BASICOS}}",
                ""
            )
        )

        # PUNTOS REVISION
        write_lines(
            ws,
            84,
            5,
            replacements.get(
                "{{PUNTOS_REVISION}}",
                ""
            )
        )

        # CONDICIONES ESPECIALES
        write_lines(
            ws,
            109,
            5,
            replacements.get(
                "{{CONDICIONES_ESPECIALES}}",
                ""
            )
        )

          write_lines(
            ws,
            76,
            5,
            replacements.get(
                "{{SERVICIOS_BASICOS}}",
                ""
            )
        )
        
        # REEMPLAZOS NORMALES
        for row in ws.iter_rows():

            for cell in row:

                if not isinstance(
                    cell.value,
                    str
                ):
                    continue

                for placeholder, value in replacements.items():

                    if placeholder.startswith("{{"):

                        if placeholder in cell.value:

                            cell.value = cell.value.replace(
                                placeholder,
                                str(value or "")
                            )

                            cell.alignment = Alignment(
                                wrap_text=True,
                                vertical="top"
                            )

    wb.save(output_path)

    return output_path
