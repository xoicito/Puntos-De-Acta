import copy

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


def _copy_row_style(ws, source_row, target_row, min_col=2, max_col=18):
    """Copy cell styles and row height from one row to another (not values)."""

    for col in range(min_col, max_col + 1):
        src = ws.cell(row=source_row, column=col)
        dst = ws.cell(row=target_row, column=col)

        if src.has_style:
            dst._style = copy.copy(src._style)

    src_dim = ws.row_dimensions.get(source_row)

    if src_dim is not None:
        ws.row_dimensions[target_row].height = src_dim.height


def _shift_row_dimensions(ws, insert_at, amount):
    """openpyxl's insert_rows() only moves cell content - it does NOT move
    row-level properties (height, hidden, customFormat), which live in
    ws.row_dimensions keyed by row number. Left alone, a hidden row (e.g.
    Condiciones Especiales) would stay hidden at its OLD row number - which
    now holds different content - while the content that moved into its old
    slot loses the hidden flag entirely. Shift those records by hand so they
    follow their row's actual content.
    """

    existing_rows = sorted(
        (r for r in ws.row_dimensions if r >= insert_at),
        reverse=True,
    )

    for row in existing_rows:
        src = ws.row_dimensions[row]
        dst = ws.row_dimensions[row + amount]
        dst.height = src.height
        dst.hidden = src.hidden
        del ws.row_dimensions[row]


def _shift_merged_ranges(ws, insert_at, amount):
    """insert_rows() does not shift merged cell ranges either - a merge that
    was at or below the insertion point stays at its old row numbers even
    though its content moved. Left alone, this produces a stale merge
    sitting on top of whatever new content lands at that row number (in our
    case, colliding with the merges written for newly-inserted rows) and
    openpyxl silently drops cell values on save when merges conflict. Move
    every affected merge down by hand instead.
    """

    to_shift = [mcr for mcr in list(ws.merged_cells.ranges) if mcr.min_row >= insert_at]

    for mcr in to_shift:
        # Not ws.unmerge_cells(): it also deletes the MergedCell placeholder
        # objects for the range, but insert_rows()'s cell-move already
        # relocated those along with everything else, so nothing is left
        # at the old position for it to delete and it raises KeyError.
        # Just drop the stale range record; merge_cells() below recreates
        # fresh placeholders at the correct (shifted) position.
        ws.merged_cells.remove(mcr)

    for mcr in to_shift:
        ws.merge_cells(
            start_row=mcr.min_row + amount,
            start_column=mcr.min_col,
            end_row=mcr.max_row + amount,
            end_column=mcr.max_col,
        )


def ensure_cotizacion_capacity(ws, needed_rows, first_row=50, template_capacity=6):
    """Insert extra rows into the Alcance de Cotizacion table if there are more
    quotation lines than the template's built-in rows can hold, and fix up the
    SUBTOTAL/IVA/TOTAL formulas that sit right below the table.

    openpyxl's insert_rows() only moves cell content - it does NOT rewrite
    formula text (so SUM(N50:N55) would silently keep pointing at the old
    range), and it does NOT shift row-level properties or merged cell
    ranges. All three are corrected by hand here - see
    _shift_row_dimensions and _shift_merged_ranges.

    Returns how many rows were inserted (0 if the template's built-in rows
    already covered `needed_rows`), so the caller can shift every hardcoded
    row number for everything below this table by the same amount.
    """

    extra = max(0, needed_rows - template_capacity)

    if not extra:
        return 0

    last_template_row = first_row + template_capacity - 1  # 55
    insert_at = last_template_row + 1  # 56

    ws.insert_rows(insert_at, extra)
    _shift_row_dimensions(ws, insert_at, extra)
    _shift_merged_ranges(ws, insert_at, extra)

    for i in range(extra):
        target_row = insert_at + i

        # Rows 50-55 alternate between two banding styles by row-number
        # parity (zebra striping) - keep extending that same pattern rather
        # than flattening every new row to one look.
        style_source_row = first_row if target_row % 2 == 0 else first_row + 1

        _copy_row_style(ws, style_source_row, target_row)
        ws.merge_cells(start_row=target_row, start_column=5, end_row=target_row, end_column=10)  # E:J
        ws.merge_cells(start_row=target_row, start_column=14, end_row=target_row, end_column=15)  # N:O

    new_last_row = last_template_row + extra
    subtotal_row = insert_at + extra  # was 56
    iva_row = subtotal_row + 1  # was 57
    total_row = subtotal_row + 2  # was 58

    ws[f"N{subtotal_row}"] = f"=SUM(N{first_row}:N{new_last_row})"
    ws[f"N{iva_row}"] = f"=+N{subtotal_row}*0.12"
    ws[f"N{total_row}"] = f"=+N{iva_row}+N{subtotal_row}"

    return extra


def write_cotizacion_rows(ws, rows):

    for offset, row in enumerate(rows):

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

    cotizacion_rows = replacements.get("__COTIZACION_ROWS__", [])

    row_shift = ensure_cotizacion_capacity(ws, len(cotizacion_rows))

    print(f"COTIZACION_ROW_SHIFT: {row_shift}")

    write_cotizacion_rows(ws, cotizacion_rows)
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

        row_num = 62 + row_shift + offset

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
        write_list_to_range(ws, 69 + row_shift, 73 + row_shift, 5, trabajos)
    elif isinstance(trabajos, str):
        write_list_to_range(ws, 69 + row_shift, 73 + row_shift, 5, trabajos.split('\n'))

    # SERVICIOS BASICOS - E76:E80 (5 rows)
    servicios = replacements.get("{{SERVICIOS_BASICOS}}", [])
    if isinstance(servicios, list):
        write_list_to_range(ws, 76 + row_shift, 80 + row_shift, 5, servicios)
    elif isinstance(servicios, str):
        write_list_to_range(ws, 76 + row_shift, 80 + row_shift, 5, servicios.split('\n'))

    # PUNTOS REVISION - E84:E98 (15 rows)
    puntos = replacements.get("{{PUNTOS_REVISION}}", [])

    write_list_to_rows(
        ws,
        list(range(84 + row_shift, 112 + row_shift)),
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

    ws[f"D{133 + row_shift}"].alignment = Alignment(
        horizontal="center",
        vertical="center"
    )

    ws[f"O{133 + row_shift}"].alignment = Alignment(
        horizontal="center",
        vertical="center"
    )

    ws[f"H{133 + row_shift}"].alignment = Alignment(
        horizontal="center",
        vertical="center"
    )

    insert_signature(
        ws,
        replacements.get("__SIGNATURE_PATH__"),
        top_left=f"D{128 + row_shift}",
        cols=("D", "E", "F"),
        rows=(128 + row_shift, 129 + row_shift, 130 + row_shift, 131 + row_shift),
    )

    wb.save(output_path)

    return output_path
