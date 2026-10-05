import re
import unicodedata
from pathlib import Path

from openpyxl import load_workbook

# Encabezados de la fila 4 de PLANTILLA_ALCANCE_COTIZACION.xlsx, en orden de
# columna. Se compara el inicio (sin tildes ni mayusculas) para aceptar tanto
# "Precio Unitario" como "Precio Unitario (sin IVA)".
ENCABEZADOS_PLANTILLA = [
    ("B", "descripcion"),
    ("C", "unidad"),
    ("D", "cantidad"),
    ("E", "precio unitario"),
    ("F", "subtotal"),
    ("G", "observaciones"),
]


def _norm(value):
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")

    return re.sub(r"\s+", " ", text).strip().lower()


def validar_plantilla(path, nombre=""):
    """None si el archivo es la plantilla oficial de Alcance de Cotizacion;
    si no, el motivo (en una frase) por el que no lo es. El lector de abajo
    asume esa estructura exacta (encabezados en la fila 4, datos desde la 5),
    asi que cualquier otro documento se leeria como basura sin avisar."""

    nombre = nombre or Path(path).name
    extension = Path(nombre).suffix.lower()

    if extension and extension not in (".xlsx", ".xlsm"):
        return f"el archivo subido ({nombre}) no es un Excel (.xlsx)"

    try:
        ws = load_workbook(path, data_only=True).active
    except Exception:
        return f"el archivo subido ({nombre}) no se pudo abrir como Excel (.xlsx)"

    faltan = [h for col, h in ENCABEZADOS_PLANTILLA if not _norm(ws[f"{col}4"].value).startswith(h)]

    if faltan:
        return (
            f"el archivo subido ({nombre}) no es la plantilla oficial: no tiene los encabezados "
            "esperados (Descripcion, Unidad, Cantidad, Precio Unitario, Subtotal, Observaciones) "
            "en la fila 4"
        )

    return None


def parse_cotizacion_upload(path):
    """Read a filled-in copy of PLANTILLA_ALCANCE_COTIZACION.xlsx and return
    a list of row dicts shaped for write_cotizacion_rows() (descripcion,
    unidad, cantidad, precio, observaciones).

    Any row with a non-empty Descripcion (column B) is included, in
    whatever order it appears - blank rows in between are just skipped, so
    it doesn't matter if the Lider leaves gaps or adds rows past the
    template's original 25.
    """

    wb = load_workbook(path, data_only=True)
    ws = wb.active

    rows = []

    for row in ws.iter_rows(min_row=5):
        descripcion = row[1].value  # column B

        if not descripcion or not str(descripcion).strip():
            continue

        rows.append({
            "descripcion": str(descripcion).strip(),
            "unidad": _text(row[2].value),
            "cantidad": _number(row[3].value),
            "precio": _number(row[4].value),
            "observaciones": _text(row[6].value),
        })

    return rows


def _text(value):
    return str(value).strip() if value is not None else ""


def _number(value):
    if value is None or value == "":
        return 0

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0
