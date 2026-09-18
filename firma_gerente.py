import base64
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import load_workbook

from config import (
    ACTA_BOARD_ID,
    ACTA_OUTPUT_DIR,
    ACTA_XLSX_COLUMN_ID,
    GERENTE_CONNECT_COLUMN_ID,
    GERENTE_EMAIL_COLUMN_ID,
    GERENTE_FIRMA_ESTADO_COLUMN_ID,
    GERENTE_FIRMA_ESTADO_FIRMADO,
    GERENTE_FIRMA_ESTADO_PENDIENTE,
    GERENTE_FIRMA_PLACEHOLDER,
    GERENTE_LINK_BASE_URL,
    GERENTE_LINK_EXPIRATION_HOURS,
    GERENTE_FIRMA_LINK_COLUMN_ID,
)
from gerente_link import InvalidLinkError, generate_signing_link, verify_token
from utils.acta_builder import item_data
from utils.excel_writer import insert_signature
from utils.monday_client import (
    change_status,
    create_update,
    get_connected_person,
    get_file_public_url,
    get_item,
    download_file,
    update_text_column,
    upload_file,
)


def start_gerente_signing(item_id, board_id):
    """Called right after a Punto de Acta is generated: resolve the real
    Gerente de Proyecto through the Connect Boards column (linked to the
    "Gerentes" board - never free text a Lider could fake), send him a
    signing link, and notify him inside Monday too.

    No-ops quietly (just logs) if the connect column isn't configured yet
    or nobody's linked - this is meant to be safe to call unconditionally
    from generate_acta.py.
    """

    if not GERENTE_CONNECT_COLUMN_ID or not GERENTE_EMAIL_COLUMN_ID:
        print("GERENTE_FIRMA: columnas de Gerente no configuradas, se omite")
        return

    item = get_item(item_id)
    name, email = get_connected_person(item, GERENTE_CONNECT_COLUMN_ID, GERENTE_EMAIL_COLUMN_ID)

    if not email:
        print(f"GERENTE_FIRMA: item={item_id} sin Gerente de Proyecto asignado, se omite")
        return

    link = generate_signing_link(item_id, board_id)

    if GERENTE_FIRMA_ESTADO_COLUMN_ID:
        change_status(item_id, board_id, GERENTE_FIRMA_ESTADO_COLUMN_ID, GERENTE_FIRMA_ESTADO_PENDIENTE)

    if GERENTE_FIRMA_LINK_COLUMN_ID:
        update_text_column(item_id, board_id, GERENTE_FIRMA_LINK_COLUMN_ID, link)

    try:
        create_update(
            item_id,
            f"El Punto de Acta esta listo para la firma de {name or 'Gerente de Proyecto'}. "
            f"Enlace de firma (valido {GERENTE_LINK_EXPIRATION_HOURS}h): {link}",
        )
    except Exception as e:
        print(f"GERENTE_FIRMA: no se pudo publicar el update en Monday: {e}")

    print(f"GERENTE_FIRMA: enlace generado para {name} <{email}> item={item_id}")


def _current_estado(item):
    if not GERENTE_FIRMA_ESTADO_COLUMN_ID:
        return ""

    for c in item.get("column_values", []):
        if c["id"] == GERENTE_FIRMA_ESTADO_COLUMN_ID:
            return (c.get("text") or "").strip()

    return ""


def _reject_if_already_signed(item):
    if _current_estado(item) == GERENTE_FIRMA_ESTADO_FIRMADO:
        raise LookupError("Este Punto de Acta ya fue firmado.")


def resolve_signing_context(token):
    """Validate the token and load what the signing page needs to show.

    Raises InvalidLinkError (bad/expired token) or LookupError (already
    signed) with a message safe to display to the signer.
    """

    data = verify_token(token)
    item_id = data["item_id"]
    board_id = data["board_id"]

    item = get_item(item_id)
    data_fields = item_data(item)

    _reject_if_already_signed(item)

    return {
        "item_id": item_id,
        "board_id": board_id,
        "proyecto": data_fields.get("proyecto", ""),
        "no_contrato": data_fields.get("no_contrato", ""),
        "empresa": data_fields.get("empresa", ""),
    }


def _save_signature_image(output_directory, stem, file_storage=None, data_url=None):
    if file_storage is not None and file_storage.filename:
        suffix = Path(file_storage.filename).suffix or ".png"
        path = str(output_directory / f"{stem}_firma_gerente{suffix}")
        file_storage.save(path)
        return path

    if data_url:
        header, _, encoded = data_url.partition(",")
        if not encoded:
            raise ValueError("Firma dibujada vacia")
        image_bytes = base64.b64decode(encoded)
        path = str(output_directory / f"{stem}_firma_gerente.png")
        Path(path).write_bytes(image_bytes)
        return path

    raise ValueError("No se recibio ninguna firma")


def apply_gerente_signature(token, file_storage=None, data_url=None, audit=None):
    """Verify the token again, insert the signature, upload the result, and
    mark the item as signed. Meant to run on the POST of the signing page -
    never trust the GET's validation alone.
    """

    data = verify_token(token)
    item_id = data["item_id"]
    board_id = data["board_id"]

    item = get_item(item_id)
    _reject_if_already_signed(item)

    editable_url = get_file_public_url(item, ACTA_XLSX_COLUMN_ID)

    if not editable_url:
        raise ValueError("El item no tiene un acta generada todavia")

    output_directory = Path(ACTA_OUTPUT_DIR)
    output_directory.mkdir(parents=True, exist_ok=True)

    stem = f"item_{item_id}"

    suffix = Path(editable_url.split("?")[0]).suffix or ".xlsx"
    source_path = str(output_directory / f"{stem}_actual{suffix}")
    download_file(editable_url, source_path)

    signature_path = _save_signature_image(
        output_directory, stem, file_storage=file_storage, data_url=data_url
    )

    wb = load_workbook(source_path)
    ws = wb["C-9-12"] if "C-9-12" in wb.sheetnames else wb.active

    signed_ok = insert_signature(
        ws,
        signature_path,
        top_left="H128",
        cols=("H", "I", "J"),
        rows=(128, 129, 130, 131),
        placeholder=GERENTE_FIRMA_PLACEHOLDER,
    )

    if not signed_ok:
        raise RuntimeError("No se pudo insertar la firma en el documento")

    signed_path = str(output_directory / f"{stem}_firmado.xlsx")
    wb.save(signed_path)

    upload_file(item_id, ACTA_XLSX_COLUMN_ID, signed_path)

    if GERENTE_FIRMA_ESTADO_COLUMN_ID:
        change_status(item_id, board_id, GERENTE_FIRMA_ESTADO_COLUMN_ID, GERENTE_FIRMA_ESTADO_FIRMADO)

    audit = audit or {}
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Written into Monday's own activity feed rather than just printed, so
    # this survives Render's log rotation - it's the actual audit record.
    try:
        create_update(
            item_id,
            f"Documento firmado por el Gerente de Proyecto el {timestamp}. "
            f"IP: {audit.get('ip', 'desconocida')} - "
            f"Dispositivo: {audit.get('user_agent', 'desconocido')}",
        )
    except Exception as e:
        print(f"GERENTE_FIRMA: no se pudo publicar el registro de auditoria: {e}")

    print(f"GERENTE_FIRMA: item={item_id} firmado - {audit}")

    return {"item_id": item_id}
