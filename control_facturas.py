from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from config import (
    ACTA_OUTPUT_DIR,
    CONTROL_FACTURAS_ANTICIPO_COLUMN_ID,
    CONTROL_FACTURAS_BOARD_ID,
    CONTROL_FACTURAS_DIVISION_COLUMN_ID,
    CONTROL_FACTURAS_EMPRESA_COLUMN_ID,
    CONTROL_FACTURAS_MONTO_COLUMN_ID,
    CONTROL_FACTURAS_NIT_COLUMN_ID,
    CONTROL_FACTURAS_PA_COLUMN_ID,
    CONTROL_FACTURAS_PROYECTO_COLUMN_ID,
    COTIZACION_FILE_COLUMN_ID,
    FIRMA_PA_ITEM_ID_COLUMN_ID,
    RUBRO_TEXT_COLUMN_ID,
)
from utils.acta_builder import item_data
from utils.cotizacion_upload import parse_cotizacion_upload
from utils.monday_client import (
    change_multiple_column_values,
    create_group,
    create_item,
    download_file,
    get_file_public_url,
    get_item,
    list_groups,
    upload_file,
)

GUATEMALA_TZ = ZoneInfo("America/Guatemala")

MESES = [
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
    "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE",
]


def _column_text(item, column_id):
    if not column_id:
        return ""

    for c in item.get("column_values", []):
        if c["id"] == column_id:
            return (c.get("text") or "").strip()

    return ""


def _week_group_title(now=None):
    """Los anticipos se agrupan por semana, con el lunes de esa semana en
    el titulo - ej. 'ANTICIPOS 5 DE OCTUBRE DE 2026', mismo formato que los
    grupos que ya existen en el board (creados a mano hasta ahora)."""

    now = now or datetime.now(GUATEMALA_TZ)
    monday = now - timedelta(days=now.weekday())

    return f"ANTICIPOS {monday.day} DE {MESES[monday.month - 1]} DE {monday.year}"


def _find_or_create_week_group(board_id, title):
    for g in list_groups(board_id):
        if g["title"].strip().lower() == title.strip().lower():
            return g["id"]

    return create_group(board_id, title)


def _monto_cotizacion(acta_item):
    """Suma cantidad x precio de cada renglon de la cotizacion subida
    (PLANTILLA_ALCANCE_COTIZACION.xlsx, ya sin IVA) - no hay un campo de
    "monto total" propio en el Punto de Acta."""

    url = get_file_public_url(acta_item, COTIZACION_FILE_COLUMN_ID)

    if not url:
        return 0

    output_directory = Path(ACTA_OUTPUT_DIR)
    output_directory.mkdir(parents=True, exist_ok=True)

    suffix = Path(url.split("?")[0]).suffix or ".xlsx"
    path = str(output_directory / f"control_facturas_cotizacion_{acta_item['id']}{suffix}")
    download_file(url, path)

    rows = parse_cotizacion_upload(path)

    return sum((r["cantidad"] or 0) * (r["precio"] or 0) for r in rows)


def _anticipo_numero(raw):
    raw = (raw or "").strip().replace("%", "").replace(",", "")

    try:
        return float(raw)
    except ValueError:
        return 0


def registrar_en_control_facturas(firma_item_id, pdf_path):
    """Llamado justo despues de que Melissa firma (ver sign_document.py).
    Crea el item correspondiente en CONTROL INGRESO DE FACTURAS, dentro
    del grupo de la semana en curso, con los datos del Punto de Acta
    original - encontrado via FIRMA_PA_ITEM_ID_COLUMN_ID ("PA ID"), la
    columna que _send_to_procurement() escribe al crear el item de
    Aprobacion.

    No lanza si algo falta (board no configurado, item viejo sin "PA ID",
    etc.) - queda para que el llamador decida si loguearlo nada mas, ya
    que esto es un registro contable adicional y no debe bloquear la
    firma de Melissa si falla.
    """

    if not CONTROL_FACTURAS_BOARD_ID:
        return

    firma_item = get_item(firma_item_id)
    acta_item_id = _column_text(firma_item, FIRMA_PA_ITEM_ID_COLUMN_ID)

    if not acta_item_id:
        print(
            f"CONTROL_FACTURAS: item={firma_item_id} sin PA ID guardado, "
            "se omite (item creado antes de esta funcionalidad)"
        )
        return

    acta_item = get_item(acta_item_id)
    data = item_data(acta_item)

    division = data.get("tipo_plantilla") or "Constructora E4"
    proyecto = data.get("proyecto") or ""
    rubro = _column_text(acta_item, RUBRO_TEXT_COLUMN_ID)
    acta_id = data.get("acta_id") or f"item-{acta_item_id}"

    name = " - ".join(part for part in (acta_id, proyecto, rubro) if part)

    title = _week_group_title()
    group_id = _find_or_create_week_group(CONTROL_FACTURAS_BOARD_ID, title)

    new_item_id = create_item(CONTROL_FACTURAS_BOARD_ID, name, group_id=group_id)

    column_values = {}

    if CONTROL_FACTURAS_DIVISION_COLUMN_ID and division:
        column_values[CONTROL_FACTURAS_DIVISION_COLUMN_ID] = {"label": division}

    if CONTROL_FACTURAS_PROYECTO_COLUMN_ID and proyecto:
        column_values[CONTROL_FACTURAS_PROYECTO_COLUMN_ID] = {"label": proyecto}

    if CONTROL_FACTURAS_EMPRESA_COLUMN_ID:
        column_values[CONTROL_FACTURAS_EMPRESA_COLUMN_ID] = data.get("empresa") or ""

    if CONTROL_FACTURAS_NIT_COLUMN_ID:
        column_values[CONTROL_FACTURAS_NIT_COLUMN_ID] = data.get("nit") or ""

    if CONTROL_FACTURAS_MONTO_COLUMN_ID:
        column_values[CONTROL_FACTURAS_MONTO_COLUMN_ID] = _monto_cotizacion(acta_item)

    if CONTROL_FACTURAS_ANTICIPO_COLUMN_ID:
        column_values[CONTROL_FACTURAS_ANTICIPO_COLUMN_ID] = _anticipo_numero(data.get("anticipo"))

    if column_values:
        change_multiple_column_values(
            new_item_id, CONTROL_FACTURAS_BOARD_ID, column_values, create_labels_if_missing=True
        )

    if CONTROL_FACTURAS_PA_COLUMN_ID and pdf_path:
        upload_file(new_item_id, CONTROL_FACTURAS_PA_COLUMN_ID, pdf_path)

    print(f"CONTROL_FACTURAS: creado item={new_item_id} ({name}) en grupo '{title}'")
