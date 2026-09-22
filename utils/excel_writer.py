import copy
import re
from datetime import datetime

from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter

from config import LIDER_FIRMA_PLACEHOLDER

SHEET_NAME = "C-9-12"

# Fixed layout of templates/100_PUNTO_DE_ACTA_PLANTILLA.xlsx. render_excel
# fills everything below at these template rows first and only then inserts
# any extra quotation rows, which pushes the rest of the sheet down - so
# nothing here ever needs adjusting for a long quotation.
COTIZACION_FIRST_ROW = 50
COTIZACION_CAPACITY = 6
PROGRAMACION_FIRST_ROW = 62
PROGRAMACION_CAPACITY = 5
TRABAJOS_FIRST_ROW = 69
SERVICIOS_FIRST_ROW = 76
SHORT_LIST_CAPACITY = 5
PUNTOS_FIRST_ROW = 84
PUNTOS_CAPACITY = 28
LIST_COLUMN = "E"

SI_NO_CELLS = {
    "{{PG_BITACORA}}": "J30",
    "{{PG_SEGURIDAD}}": "J31",
    "{{PG_PROTOCOLO}}": "J32",
    "{{PG_REUNION}}": "J33",
    "{{PG_SUPERVISOR}}": "J34",
    "{{PG_ENCARGADO}}": "J35",
    "{{PL_ARQ}}": "J38",
    "{{PL_COTAS}}": "J39",
    "{{PL_ELEV}}": "J40",
    "{{PL_HIDRO}}": "J41",
    "{{PL_ELEC}}": "J42",
    "{{PL_ACAB}}": "J43",
    "{{PL_ESTR_PRIN}}": "J44",
    "{{PL_ESTR_SEC}}": "J45",
    "{{PL_OBRAS}}": "J46",
}

MULTA_CELLS = {
    "{{MULTA_ATRASO}}": "P30",
    "{{MULTA_ORDEN}}": "P31",
    "{{MULTA_SEGURIDAD}}": "P32",
    "{{MULTA_REPORTERIA}}": "P33",
}

# Written row by row by the functions below, never by plain text replacement.
LIST_PLACEHOLDERS = {
    "{{PROGRAMACION}}",
    "{{TRABAJOS_PREVIOS}}",
    "{{SERVICIOS_BASICOS}}",
    "{{PUNTOS_REVISION}}",
}

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


def insert_signature(ws, signature_path, placeholder):
    """Insert an image scaled to fit, without distortion, inside the cell (or
    merged range) that holds `placeholder`, and clear the placeholder text.

    Finding the box by its text - instead of by fixed cell coordinates -
    keeps the signature in the right place no matter how many rows were
    inserted above it.

    Returns True if the image was inserted, False otherwise. Callers that treat
    the signature as a required step (e.g. an approval signing flow) should
    check this and avoid publishing the document as "signed" on failure.
    """

    if not signature_path:
        return False

    found = _find_placeholder_box(ws, placeholder)

    if not found:
        print(f"ERROR FIRMA_IMAGEN: no se encontro el marcador {placeholder}")
        return False

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
    row-level properties (height, hidden), which live in ws.row_dimensions
    keyed by row number. Shift those records by hand so they follow their
    row's actual content.
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


def _shift_print_layout(ws, insert_at, amount):
    """Keep the print area and manual page breaks in step with inserted
    rows - otherwise the bottom of the document (the signature block) falls
    outside the print area and the page-3 break lands in the wrong place.
    """

    for page_break in ws.row_breaks.brk:
        if page_break.id >= insert_at:
            page_break.id += amount

    match = re.search(r"\$([A-Z]+)\$(\d+):\$([A-Z]+)\$(\d+)$", ws.print_area or "")

    if match:
        first_col, first_row, last_col, last_row = match.groups()
        ws.print_area = f"{first_col}{first_row}:{last_col}{int(last_row) + amount}"


def ensure_cotizacion_capacity(ws, needed_rows):
    """Insert extra rows into the Alcance de Cotizacion table if there are more
    quotation lines than the template's built-in rows can hold, and fix up the
    SUBTOTAL/IVA/TOTAL formulas that sit right below the table.

    openpyxl's insert_rows() only moves cell content - it does NOT rewrite
    formula text (so SUM(N50:N55) would silently keep pointing at the old
    range), and it does NOT shift row-level properties, merged cell ranges,
    the print area or page breaks. All of those are corrected by hand here.

    Returns how many rows were inserted.
    """

    extra = max(0, needed_rows - COTIZACION_CAPACITY)

    if not extra:
        return 0

    first_row = COTIZACION_FIRST_ROW
    last_template_row = first_row + COTIZACION_CAPACITY - 1
    insert_at = last_template_row + 1

    ws.insert_rows(insert_at, extra)
    _shift_row_dimensions(ws, insert_at, extra)
    _shift_merged_ranges(ws, insert_at, extra)
    _shift_print_layout(ws, insert_at, extra)

    for i in range(extra):
        target_row = insert_at + i

        # The template rows alternate between two banding styles by row-number
        # parity (zebra striping) - keep extending that same pattern rather
        # than flattening every new row to one look.
        style_source_row = first_row if target_row % 2 == 0 else first_row + 1

        _copy_row_style(ws, style_source_row, target_row)
        ws.merge_cells(start_row=target_row, start_column=5, end_row=target_row, end_column=10)  # E:J
        ws.merge_cells(start_row=target_row, start_column=14, end_row=target_row, end_column=15)  # N:O

    new_last_row = last_template_row + extra
    subtotal_row = insert_at + extra
    iva_row = subtotal_row + 1
    total_row = subtotal_row + 2

    ws[f"N{subtotal_row}"] = f"=SUM(N{first_row}:N{new_last_row})"
    ws[f"N{iva_row}"] = f"=+N{subtotal_row}*0.12"
    ws[f"N{total_row}"] = f"=+N{iva_row}+N{subtotal_row}"

    return extra


def write_cotizacion_rows(ws, rows):

    for offset, row in enumerate(rows):
        excel_row = COTIZACION_FIRST_ROW + offset

        ws[f"D{excel_row}"] = offset + 1
        ws[f"E{excel_row}"] = row.get("descripcion", "")
        ws[f"K{excel_row}"] = row.get("unidad", "")
        ws[f"L{excel_row}"] = row.get("cantidad", "")
        ws[f"M{excel_row}"] = row.get("precio", "")
        ws[f"N{excel_row}"] = float(row.get("cantidad") or 0) * float(row.get("precio") or 0)
        ws[f"P{excel_row}"] = row.get("observaciones", "")


def _as_lines(value):
    """Normalize a list, a newline-separated string or None into a list of
    non-empty strings."""

    if not value:
        return []

    items = value if isinstance(value, list) else str(value).split("\n")

    return [str(item) for item in items if str(item).strip()]


def _write_list(ws, first_row, capacity, items, column=LIST_COLUMN, row_shift=0):
    """Fill `capacity` consecutive rows of one column with `items`.

    Every row in the range is written, empty ones included, so a placeholder
    left over from the template can never show up in the finished document
    when there are fewer items than rows (or none at all). Items beyond the
    table's capacity are dropped, with a log line.
    """

    if len(items) > capacity:
        print(f"AVISO: {len(items)} lineas para {capacity} filas en {column}{first_row}, se omiten {len(items) - capacity}")

    for i in range(capacity):
        cell = ws[f"{column}{first_row + row_shift + i}"]

        if i < len(items):
            cell.value = str(items[i])
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        else:
            cell.value = None


def _days_between(inicio, fin):
    """Inclusive number of days between two DD/MM/YYYY dates, or None if
    either is missing or malformed."""

    try:
        start = datetime.strptime(inicio, "%d/%m/%Y")
        end = datetime.strptime(fin, "%d/%m/%Y")
    except (TypeError, ValueError):
        return None

    return (end - start).days + 1


def _write_programacion(ws, rows, row_shift=0):
    """Programacion de Fechas: AREA (D), INICIO (G), TERMINA (I), DIAS (K),
    OBSERVACIONES (M). Unused rows are cleared, same as _write_list."""

    if len(rows) > PROGRAMACION_CAPACITY:
        print(f"AVISO: {len(rows)} filas de programacion para {PROGRAMACION_CAPACITY}, se omiten las sobrantes")

    for i in range(PROGRAMACION_CAPACITY):
        row_num = PROGRAMACION_FIRST_ROW + row_shift + i
        fila = rows[i] if i < len(rows) else {}

        ws[f"D{row_num}"] = fila.get("area") or None
        ws[f"G{row_num}"] = fila.get("inicio") or None
        ws[f"I{row_num}"] = fila.get("fin") or None
        ws[f"K{row_num}"] = _days_between(fila.get("inicio"), fila.get("fin"))
        ws[f"M{row_num}"] = fila.get("obs") or None


def _replace_text_placeholders(ws, replacements):
    """Replace {{PLACEHOLDER}} text wherever it appears, leaving each cell's
    own formatting (e.g. centered percentages) untouched."""

    text_placeholders = {
        placeholder: value
        for placeholder, value in replacements.items()
        if placeholder.startswith("{{")
        and placeholder.endswith("}}")
        and placeholder not in LIST_PLACEHOLDERS
    }

    for row in ws.iter_rows():
        for cell in row:
            if not isinstance(cell.value, str) or "{{" not in cell.value:
                continue

            for placeholder, value in text_placeholders.items():
                if placeholder not in cell.value:
                    continue

                text = "\n".join(str(v) for v in value) if isinstance(value, list) else str(value or "")
                cell.value = cell.value.replace(placeholder, text)


def render_excel(template_path, output_path, replacements):

    wb = load_workbook(template_path)
    ws = wb[SHEET_NAME]

    print(f"IMAGENES CARGADAS DE LA PLANTILLA: {len(ws._images)}")

    for placeholder, cell in SI_NO_CELLS.items():
        ws[cell] = replacements.get(placeholder, "NO")

    for placeholder, cell in MULTA_CELLS.items():
        ws[cell] = replacements.get(placeholder, "")

    # First on purpose: the quotation table sits above everything else this
    # function writes, so growing it shifts every row number below.
    cotizacion_rows = replacements.get("__COTIZACION_ROWS__", [])
    row_shift = ensure_cotizacion_capacity(ws, len(cotizacion_rows))
    print(f"COTIZACION_FILAS_EXTRA: {row_shift}")
    write_cotizacion_rows(ws, cotizacion_rows)

    _write_programacion(ws, replacements.get("__PROGRAMACION_ROWS__", []), row_shift)

    _write_list(ws, TRABAJOS_FIRST_ROW, SHORT_LIST_CAPACITY, _as_lines(replacements.get("{{TRABAJOS_PREVIOS}}")), row_shift=row_shift)
    _write_list(ws, SERVICIOS_FIRST_ROW, SHORT_LIST_CAPACITY, _as_lines(replacements.get("{{SERVICIOS_BASICOS}}")), row_shift=row_shift)
    _write_list(ws, PUNTOS_FIRST_ROW, PUNTOS_CAPACITY, _as_lines(replacements.get("{{PUNTOS_REVISION}}")), row_shift=row_shift)

    _replace_text_placeholders(ws, replacements)

    # Placeholder-based, so it's found wherever it landed - no row_shift needed.
    insert_signature(ws, replacements.get("__SIGNATURE_PATH__"), LIDER_FIRMA_PLACEHOLDER)

    wb.save(output_path)

    return output_path
