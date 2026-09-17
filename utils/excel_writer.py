from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter

DEFAULT_COL_WIDTH = 8.43
DEFAULT_ROW_HEIGHT = 15.0
MAX_DIGIT_WIDTH = 7


def _col_width_px(ws, col_letter):
    width = ws.column_dimensions[col_letter].width
    if width is None:
        width = DEFAULT_COL_WIDTH
    return int((256 * width + int(128 / MAX_DIGIT_WIDTH)) / 256 * MAX_DIGIT_WIDTH)


def _row_height_px(ws, row):
    height = ws.row_dimensions[row].height
    if height is None:
        height = DEFAULT_ROW_HEIGHT
    return int(height * 96 / 72)


def _find_placeholder_box(ws, placeholder):
    """Locate a text placeholder in the sheet and return its (top_left, cols, rows) box.

    If the placeholder's cell is part of a merged range, the whole merged range
    becomes the box. Otherwise the single cell is used. The placeholder text is
    cleared from the cell either way. Returns None if the placeholder isn't found.
    """

    for row in ws.iter_rows():
        for cell in row:
            if not isinstance(cell.value, str) or placeholder not in cell.value:
                continue

            for merged_range in ws.merged_cells.ranges:
                if cell.coordinate in merged_range:
                    cols = tuple(
                        get_column_letter(c)
                        for c in range(merged_range.min_col, merged_range.max_col + 1)
                    )
                    rows_box = tuple(
                        range(merged_range.min_row, merged_range.max_row + 1)
                    )
                    cell.value = cell.value.replace(placeholder, "").strip() or None
                    return (
                        f"{get_column_letter(merged_range.min_col)}{merged_range.min_row}",
                        cols,
                        rows_box,
                    )

            col_letter = get_column_letter(cell.column)
            cell.value = cell.value.replace(placeholder, "").strip() or None
            return cell.coordinate, (col_letter,), (cell.row,)

    return None


def insert_signature(ws, signature_path, top_left, cols, rows, placeholder=None):
    """Insert an image scaled to fit inside a box without distorting it.

    If `placeholder` is given and found somewhere in the sheet, its cell (or
    merged range) is used as the box instead of the fixed top_left/cols/rows
    arguments, and the placeholder text is cleared. This lets different
    template variants place the signature wherever they need to just by
    containing that placeholder text, instead of relying on a fixed cell
    range that only matches one template layout. If the placeholder isn't
    found (or isn't given), the fixed box is used as-is.

    Returns True if the image was inserted, False otherwise. Callers that treat
    the signature as a required step (e.g. an approval signing flow) should
    check this and avoid publishing the document as "signed" on failure.
    """

    if not signature_path:
        return False

    if placeholder:
        found = _find_placeholder_box(ws, placeholder)
        if found:
            top_left, cols, rows = found

    try:
        img = XLImage(signature_path)

        box_w = sum(_col_width_px(ws, c) for c in cols)
        box_h = sum(_row_height_px(ws, r) for r in rows)

        scale = min(box_w / img.width, box_h / img.height)

        img.width = int(img.width * scale)
        img.height = int(img.height * scale)

        ws.add_image(img, top_left)

        return True

    except Exception as e:
        print(f"ERROR FIRMA_IMAGEN: {e}")
        return False


def write_cotizacion_rows(ws, rows):

    for offset, row in enumerate(rows[:6]):

        excel_row = 50 + offset

        values = [
            (f"D{excel_row}", offset + 1),
            (f"E{excel_row}", row.get("descripcion", "")),
            (f"K{excel_row}", row.get("unidad", "")),
            (f"L{excel_row}", row.get("cantidad", "")),
            (f"M{excel_row}", row.get("precio", "")),
            (f"P{excel_row}", row.get("observaciones", "")),
        ]

        for cell_ref, value in values:

            try:
                ws[cell_ref] = value
            except Exception as e:
                print(f"ERROR_COTIZACION {cell_ref} -> {e}")
                raise

        try:

            subtotal = (
                float(row.get("cantidad", 0))
                *
                float(row.get("precio", 0))
            )

            ws[f"N{excel_row}"] = subtotal
            try:
                ws[f"N{excel_row}"] = subtotal
            except Exception:
                ws[f"O{excel_row}"] = subtotal

        except Exception as e:

            print(
                f"ERROR_SUBTOTAL N{excel_row} -> {e}"
            )

            raise


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

    wb = load_workbook(template_path)

    ws = wb["C-9-12"]

    print(f"IMAGENES CARGADAS DE LA PLANTILLA: {len(ws._images)}")

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

        for celda, valor in [
            (f"D{row_num}", fila.get("area", "")),
            (f"G{row_num}", fila.get("inicio", "")),
            (f"I{row_num}", fila.get("fin", "")),
        ]:

            try:
                ws[celda] = valor
            except Exception as e:
                print(f"ERROR PROGRAMACION {celda}: {e}")
                raise

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

        except Exception as e:
            print(f"ERROR PROGRAMACION K{row_num}: {e}")
            raise

        try:
            ws[f"M{row_num}"] = fila.get("obs", "")
        except Exception as e:
            print(f"ERROR PROGRAMACION M{row_num}: {e}")
            raise

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
        list(range(84, 112)),
        5,
        puntos
    )

    # REEMPLAZOS NORMALES - Text placeholders in cells
    for row in ws.iter_rows():
        for cell in row:
            if not isinstance(cell.value, str):
                continue

            for placeholder, value in replacements.items():
                # Skip list placeholders and special keys
                if placeholder.startswith("{{") and placeholder.endswith("}}"):
                    if placeholder in ["{{PROGRAMACION}}", "{{TRABAJOS_PREVIOS}}",
                                     "{{SERVICIOS_BASICOS}}", "{{PUNTOS_REVISION}}"]:
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

                        # Alignment intentionally left untouched here so the
                        # template's own per-cell formatting (e.g. centered
                        # percentage fields) survives the replacement.

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

    insert_signature(
        ws,
        replacements.get("__SIGNATURE_PATH__"),
        top_left="D128",
        cols=("D", "E", "F"),
        rows=(128, 129, 130, 131),
    )

    wb.save(output_path)

    return output_path
