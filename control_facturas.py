import re
import unicodedata
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
    create_update,
    download_file,
    get_file_public_url,
    get_item,
    get_status_labels,
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
    # El grupo lleva el lunes en que se ingresa el anticipo, que es el lunes
    # SIGUIENTE a la semana en que se registra: lo que entra de lunes a
    # domingo de la semana del 28 de septiembre va al grupo del 5 de octubre.
    monday = now + timedelta(days=7 - now.weekday())

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


def _norm(text):
    text = unicodedata.normalize("NFD", str(text or ""))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def _match_label(existing, wanted):
    """Find the existing label that corresponds to `wanted` ("Reforma" ->
    "REFORMA E4", "MC Villa Nueva" -> "MC VILLA NUEVA"). Returns None when
    nothing matches, so the caller can leave the column empty instead of
    letting Monday invent a duplicate label."""

    target = _norm(wanted)

    if not target:
        return None

    normed = [(label, _norm(label)) for label in existing]

    for label, n in normed:
        if n == target:
            return label

    for label, n in normed:
        if n.startswith(target + " ") or target.startswith(n + " "):
            return label

    return None


def _nit_sin_guion(nit):
    return re.sub(r"[\s-]+", "", nit or "")


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

    name = rubro or acta_id

    title = _week_group_title()
    group_id = _find_or_create_week_group(CONTROL_FACTURAS_BOARD_ID, title)

    new_item_id = create_item(CONTROL_FACTURAS_BOARD_ID, name, group_id=group_id)

    column_values = {}
    sin_etiqueta = []

    # Las etiquetas ya existen en el board ("REFORMA E4", "MC VILLA NUEVA"):
    # se busca la equivalente en vez de pedirle a Monday que cree una
    # (create_labels_if_missing) - eso duplicaba la etiqueta ante cualquier
    # diferencia de mayusculas o de texto ("Reforma" vs "REFORMA E4").
    for column_id, wanted, nombre in (
        (CONTROL_FACTURAS_DIVISION_COLUMN_ID, division, "DIVISIÓN"),
        (CONTROL_FACTURAS_PROYECTO_COLUMN_ID, proyecto, "PROYECTO"),
    ):
        if not column_id or not wanted:
            continue

        label = _match_label(get_status_labels(CONTROL_FACTURAS_BOARD_ID, column_id), wanted)

        if label:
            column_values[column_id] = {"label": label}
        else:
            sin_etiqueta.append(f"{nombre}: '{wanted}'")

    if CONTROL_FACTURAS_EMPRESA_COLUMN_ID:
        column_values[CONTROL_FACTURAS_EMPRESA_COLUMN_ID] = data.get("empresa") or ""

    if CONTROL_FACTURAS_NIT_COLUMN_ID:
        column_values[CONTROL_FACTURAS_NIT_COLUMN_ID] = _nit_sin_guion(data.get("nit"))

    if CONTROL_FACTURAS_MONTO_COLUMN_ID:
        column_values[CONTROL_FACTURAS_MONTO_COLUMN_ID] = _monto_cotizacion(acta_item)

    if CONTROL_FACTURAS_ANTICIPO_COLUMN_ID:
        column_values[CONTROL_FACTURAS_ANTICIPO_COLUMN_ID] = _anticipo_numero(data.get("anticipo"))

    if column_values:
        change_multiple_column_values(
            new_item_id, CONTROL_FACTURAS_BOARD_ID, column_values
        )

    if sin_etiqueta:
        print(f"CONTROL_FACTURAS: item={new_item_id} sin etiqueta equivalente - {', '.join(sin_etiqueta)}")
        try:
            create_update(
                new_item_id,
                "No se encontro una etiqueta existente para: " + ", ".join(sin_etiqueta)
                + ". Esa columna se dejo vacia - elige la etiqueta correcta a mano.",
            )
        except Exception as e:
            print(f"CONTROL_FACTURAS: no se pudo publicar el aviso de etiqueta: {e}")

    if CONTROL_FACTURAS_PA_COLUMN_ID and pdf_path:
        upload_file(new_item_id, CONTROL_FACTURAS_PA_COLUMN_ID, pdf_path)

    print(f"CONTROL_FACTURAS: creado item={new_item_id} ({name}) en grupo '{title}'")
