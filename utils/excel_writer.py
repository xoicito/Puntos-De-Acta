                   
from openpyxl import load_workbook
from openpyxl.styles import Alignment


def write_cotizacion_rows(ws, rows):

    for offset, row in enumerate(rows[:6]):

        excel_row = 50 + offset

    ws[f"D{row_num}"] = fila.get("area", "")
    ws[f"G{row_num}"] = fila.get("inicio", "")
    ws[f"I{row_num}"] = fila.get("fin", "")
    
    try:
        from datetime import datetime
    
        inicio = datetime.strptime(
            fila.get("inicio", ""),
            "%d/%m/%Y"
        )
    
        fin = datetime.strptime(
            fila.get("fin", ""),
            "%d/%m/%Y"
        )
    
        ws[f"K{row_num}"] = (fin - inicio).days + 1
    
    except Exception:
        ws[f"K{row_num}"] = ""
    
    ws[f"M{row_num}"] = fila.get("obs", "")


      
        try:

            subtotal = (
                float(
                    row.get(
                        "cantidad",
                        0
                    )
                )
                *
                float(
                    row.get(
                        "precio",
                        0
                    )
                )
            )

            ws[f"N{excel_row}"] = subtotal

        except Exception:
            pass

        ws[f"P{excel_row}"] = row.get(
            "observaciones",
            ""
        )


def write_list_to_range(ws, start_row, end_row, column, items):

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
                horizontal="center",
                vertical="center",
                wrap_text=True
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
            horizontal="center",
            vertical="center",
            wrap_text=True
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

    wb = load_workbook(template_path)

    ws = wb["C-9-12"]
    
    write_cotizacion_rows(
        ws,
        replacements.get(
            "__COTIZACION_ROWS__",
            []
        )
    )
    # PUNTOS GENERALES

    ws["J30"] = replacements.get("{{PG_BITACORA}}", "NO")
    ws["J31"] = replacements.get("{{PG_SEGURIDAD}}", "NO")
    ws["J32"] = replacements.get("{{PG_PROTOCOLO}}", "NO")
    ws["J33"] = replacements.get("{{PG_REUNION}}", "NO")
    ws["J34"] = replacements.get("{{PG_SUPERVISOR}}", "NO")
    ws["J35"] = replacements.get("{{PG_ENCARGADO}}", "NO")
    
    # PLANOS ENTREGADOS
    
    ws["J38"] = replacements.get("{{PL_ARQ}}", "NO")
    ws["J39"] = replacements.get("{{PL_COTAS}}", "NO")
    ws["J40"] = replacements.get("{{PL_ELEV}}", "NO")
    ws["J41"] = replacements.get("{{PL_HIDRO}}", "NO")
    ws["J42"] = replacements.get("{{PL_ELEC}}", "NO")
    ws["J43"] = replacements.get("{{PL_ACAB}}", "NO")
    ws["J44"] = replacements.get("{{PL_ESTR_PRIN}}", "NO")
    ws["J45"] = replacements.get("{{PL_ESTR_SEC}}", "NO")
    ws["J46"] = replacements.get("{{PL_OBRAS}}", "NO")

    # -------------------------
    # PUNTOS GENERALES
    # -------------------------
    
    ws["J30"] = replacements.get(
        "{{PG_BITACORA}}",
        "NO"
    )
    
    ws["J31"] = replacements.get(
        "{{PG_SEGURIDAD}}",
        "NO"
    )
    
    ws["J32"] = replacements.get(
        "{{PG_PROTOCOLO}}",
        "NO"
    )
    
    ws["J33"] = replacements.get(
        "{{PG_REUNION}}",
        "NO"
    )
    
    ws["J34"] = replacements.get(
        "{{PG_SUPERVISOR}}",
        "NO"
    )
    
    ws["J35"] = replacements.get(
        "{{PG_ENCARGADO}}",
        "NO"
    )

    ws["P30"] = replacements.get("{{MULTA_ATRASO}}", "")
    ws["P31"] = replacements.get("{{MULTA_ORDEN}}", "")
    ws["P32"] = replacements.get("{{MULTA_SEGURIDAD}}", "")
    ws["P33"] = replacements.get("{{MULTA_REPORTERIA}}", "")
    
    # -------------------------
    # PLANOS ENTREGADOS
    # -------------------------
    
    ws["J38"] = replacements.get(
        "{{PL_ARQ}}",
        "NO"
    )
    
    ws["J39"] = replacements.get(
        "{{PL_COTAS}}",
        "NO"
    )
    
    ws["J40"] = replacements.get(
        "{{PL_ELEV}}",
        "NO"
    )
    
    ws["J41"] = replacements.get(
        "{{PL_HIDRO}}",
        "NO"
    )
    
    ws["J42"] = replacements.get(
        "{{PL_ELEC}}",
        "NO"
    )
    
    ws["J43"] = replacements.get(
        "{{PL_ACAB}}",
        "NO"
    )
    
    ws["J44"] = replacements.get(
        "{{PL_ESTR_PRIN}}",
        "NO"
    )
    
    ws["J45"] = replacements.get(
        "{{PL_ESTR_SEC}}",
        "NO"
    )
    
    ws["J46"] = replacements.get(
        "{{PL_OBRAS}}",
        "NO"
    )

    programacion_rows = replacements.get(
        "__PROGRAMACION_ROWS__",
        []
    )
    
    for offset, fila in enumerate(programacion_rows[:5]):
    
        row_num = 62 + offset
    
        ws[f"D{row_num}"] = fila.get("area", "")
        ws[f"G{row_num}"] = fila.get("inicio", "")
        ws[f"J{row_num}"] = fila.get("fin", "")
        
        try:
            from datetime import datetime
        
            inicio = datetime.strptime(
                fila.get("inicio", ""),
                "%d/%m/%Y"
            )
        
            fin = datetime.strptime(
                fila.get("fin", ""),
                "%d/%m/%Y"
            )
        
            ws[f"M{row_num}"] = (
                fin - inicio
            ).days + 1
        
        except Exception:
            ws[f"M{row_num}"] = ""
        
        ws[f"N{row_num}"] = fila.get("obs", "")
    
        for col in ["D", "G", "J", "M"]:
    
            ws[f"{col}{row_num}"].alignment = Alignment(
                wrap_text=True,
                vertical="top"
            )

        for celda in ["D62", "G62", "J62", "M62"]:

            ws[celda].alignment = Alignment(
                wrap_text=True,
                vertical="top"
            )

    # aquí sigue el resto del código...

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
            write_list_to_range(ws, 115, 122, 5, condiciones)
        elif isinstance(condiciones, str):
            write_list_to_range(ws, 115, 122, 5, condiciones.split('\n'))

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
                                horizontal="center",
                                vertical="center",
                                wrap_text=True
                            )

    ws["D133"].alignment = Alignment(
        horizontal="center",
        vertical="center"
    )
    
    ws["O133"].alignment = Alignment(
        horizontal="center",
        vertical="center"
    )

    ws["H133"].alignment = Alignment(
        horizontal="center",
        vertical="center"
    )
    
    
    wb.save(output_path)

    return output_path
