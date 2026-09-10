from openpyxl import load_workbook
from openpyxl.styles import Alignment


def write_list_to_range(ws, start_row, end_row, column, items):
    """Write list items to a range of cells, respecting the boundaries."""

    for i, item in enumerate(items):

        row = start_row + i

        if row > end_row:
            break

        try:

            cell = ws.cell(row=row, column=column)

            print(
                f"INTENTANDO row={row} col={column} tipo={type(cell).__name__}"
            )

            cell.value = str(item)

            cell.alignment = Alignment(
                wrap_text=True,
                vertical="top"
            )

        except Exception as e:

            print(
                f"ERROR CELDA row={row} col={column} "
                f"tipo={type(cell).__name__} "
                f"item={item} "
                f"error={e}"
            )

            raise

def write_list_to_rows(ws, rows, column, items):

    for row, item in zip(rows, items):

        cell = ws.cell(row=row, column=column)

        cell.value = str(item)

        cell.alignment = Alignment(
            wrap_text=True,
            vertical="top"
        )

def write_programacion_row(ws, row_num, area, inicio, fin, obs):
    """Write a single programacion row to the specified columns."""
    ws.cell(row=row_num, column=4).value = area  # D
    ws.cell(row=row_num, column=7).value = inicio  # G
    ws.cell(row=row_num, column=10).value = fin  # J
    ws.cell(row=row_num, column=13).value = obs  # M

    for col in [4, 7, 10, 13]:
        ws.cell(row=row_num, column=col).alignment = Alignment(
            wrap_text=True,
            vertical="top"
        )


def render_excel(template_path, output_path, replacements):
    print("=== RENDER EXCEL INICIADO ===")
    """Render Excel template with replacements and list data in proper cell ranges."""
    wb = load_workbook(template_path)

    for ws in wb.worksheets:

        programacion_rows = replacements.get(
            "__PROGRAMACION_ROWS__",
            []
        )
        
        if programacion_rows:
        
            fila = programacion_rows[0]
        
            ws["D62"] = fila.get("area", "")
            ws["G62"] = fila.get("inicio", "")
            ws["J62"] = fila.get("fin", "")
            ws["M62"] = fila.get("obs", "")
        
            for celda in ["D62", "G62", "J62", "M62"]:
        
                ws[celda].alignment = Alignment(
                    wrap_text=True,
                    vertical="top"
                )

        # TRABAJOS PREVIOS - E69:E73 (5 rows)
        print("TRABAJOS_PREVIOS")
        trabajos = replacements.get("{{TRABAJOS_PREVIOS}}", [])
        if isinstance(trabajos, list):
            write_list_to_range(ws, 69, 73, 5, trabajos)
        elif isinstance(trabajos, str):
            write_list_to_range(ws, 69, 73, 5, trabajos.split('\n'))

        # SERVICIOS BASICOS - E76:E80 (5 rows)
        servicios = replacements.get("{{SERVICIOS_BASICOS}}", [])
        if isinstance(servicios, list):
            write_list_to_range(ws, 76, 80, 5, servicios)
        elif isinstance(servicios, str):
            write_list_to_range(ws, 76, 80, 5, servicios.split('\n'))

        # PUNTOS REVISION - E84:E98 (15 rows)
        puntos = replacements.get("{{PUNTOS_REVISION}}", [])
        
        write_list_to_rows(
            ws,
            [84, 86, 88, 90, 92, 94, 96, 98],
            5,
            puntos
        )

        # CONDICIONES ESPECIALES - E109:E116 (8 rows)
        condiciones = replacements.get("{{CONDICIONES_ESPECIALES}}", [])
        if isinstance(condiciones, list):
            write_list_to_range(ws, 109, 116, 5, condiciones)
        elif isinstance(condiciones, str):
            write_list_to_range(ws, 109, 116, 5, condiciones.split('\n'))

        # REEMPLAZOS NORMALES - Text placeholders in cells
        for row in ws.iter_rows():
            for cell in row:
                if not isinstance(cell.value, str):
                    continue

                for placeholder, value in replacements.items():
                    # Skip list placeholders and special keys
                    if placeholder.startswith("{{") and placeholder.endswith("}}"):
                        if placeholder in ["{{PROGRAMACION}}", "{{TRABAJOS_PREVIOS}}", 
                                         "{{SERVICIOS_BASICOS}}", "{{PUNTOS_REVISION}}", 
                                         "{{CONDICIONES_ESPECIALES}}"]:
                            continue

                        if placeholder in cell.value:
                            if isinstance(value, list):
                                cell.value = cell.value.replace(
                                    placeholder,
                                    "\n".join(str(v) for v in value)
                                )
                            else:
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
