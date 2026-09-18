import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from config import (
    ACTA_BOARD_ID,
    ACTA_ID_COLUMN_ID,
    ACTA_OUTPUT_DIR,
    ACTA_STATUS_COLUMN_ID,
    ACTA_TEMPLATE,
    ACTA_XLSX_COLUMN_ID,
    COTIZACION_FILE_COLUMN_ID,
    FIRMA_MONDAY_COLUMN_ID,
    METODO_FIRMA_MONDAY_LABEL,
    SIGNATURE_COLUMN_ID,
)
from utils.monday_client import (
    change_status,
    create_update,
    download_file,
    generate_acta_id,
    get_file_public_url,
    get_item,
    upload_file,
    update_text_column,
)
from utils.acta_builder import build_blocks, display_date, item_data, pct
from utils.cotizacion_upload import parse_cotizacion_upload
from utils.excel_writer import render_excel
from firma_gerente import start_gerente_signing


def _clean(value):
    return re.sub(r"[^A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ._-]+", "_", str(value or "")).strip("_")


GUATEMALA_TZ = ZoneInfo("America/Guatemala")


def _is_late_submission(now=None):
    """Per the Politica de Aprobacion de Puntos de Acta: requests are
    accepted Monday 7:00am to Wednesday 10:00am (Guatemala time). Outside
    that window the request is actually queued for the following week's
    review cycle - this only flags it, doesn't block generation.
    """

    now = now or datetime.now(GUATEMALA_TZ)
    weekday = now.weekday()  # Monday=0 ... Sunday=6

    if weekday == 0:  # lunes
        return now.hour < 7
    if weekday == 1:  # martes
        return False
    if weekday == 2:  # miercoles
        return (now.hour, now.minute) >= (10, 0)

    return True  # jueves-domingo


def generate_acta(item_id):
    item = get_item(item_id)
    data = item_data(item)

    board_id = int(data.get("board_id") or ACTA_BOARD_ID)

    if not data.get("acta_id"):
        data["acta_id"] = generate_acta_id()
        update_text_column(item_id, board_id, ACTA_ID_COLUMN_ID, data["acta_id"])

    print("ACTA_ID =", data.get("acta_id"))
    print("PUNTOS_GENERALES:", data.get("puntos_generales"))
    print("PLANOS_ENTREGADOS:", data.get("planos_entregados"))
    print("MULTAS_APLICAR =", data.get("multas_aplicar"))

    if _is_late_submission():
        print("SOLICITUD FUERA DE PLAZO (Lunes 7:00am - Miercoles 10:00am)")
        try:
            create_update(
                item_id,
                "Esta solicitud se recibio fuera del horario oficial "
                "(Lunes 7:00am a Miercoles 10:00am) segun la Politica de "
                "Aprobacion de Puntos de Acta. Sera programada para el "
                "siguiente ciclo de revision semanal.",
            )
        except Exception as e:
            print(f"ERROR_LATE_FLAG: {e}")

    change_status(item_id, board_id, ACTA_STATUS_COLUMN_ID, "Procesando")

    try:
        base = Path(__file__).resolve().parent

        rubrics = json.loads((base / "rubros.json").read_text(encoding="utf-8"))

        replacements = {
            "{{PROYECTO}}": data["proyecto"].upper(),
            "{{LIDER}}": data.get("lider_proyecto", "").upper(),
            "{{RUBRO}}": data["rubro"].upper(),
            "{{TIPO_CONTRATO}}": data["tipo_contrato"].upper(),
            "{{EMPRESA}}": data["empresa"].upper(),
            "{{CONTACTO}}": data["contacto"].upper(),
            "{{TELEFONO}}": data["telefono"],
            "{{NIT}}": data["nit"],
            "{{GERENTE_PROYECTO}}":data.get("gerente_proyecto","").upper(),
            "{{NO_COTIZACION}}": data["no_cotizacion"],
            "{{ANTICIPO}}": pct(data["anticipo"]),
            "{{ESTIMACIONES}}": pct(data["estimaciones"]),
            "{{CONTRA_ENTREGA}}": pct(data["contra_entrega"]),
            "{{RETENIDO}}": pct(data["retenido"]),
            "{{NO_CONTRATO}}": data["no_contrato"],
            "{{FECHA_ACTA}}": display_date(data["fecha_acta"]),
        }

        replacements.update(build_blocks(data, rubrics))

        missing = [f for f in ("proyecto", "rubro", "no_contrato", "empresa") if not data.get(f)]

        if missing:
            raise ValueError("Campos obligatorios vacíos: " + ", ".join(missing))

        stem = _clean(f"PA-{data['no_contrato']}-{data['rubro']}-{data['proyecto']}")[:140]

        output_directory = Path(ACTA_OUTPUT_DIR)
        output_directory.mkdir(parents=True, exist_ok=True)

        xlsx = str(output_directory / f"{stem}.xlsx")

        cotizacion_rows = []

        try:
            if COTIZACION_FILE_COLUMN_ID:
                cotizacion_url = get_file_public_url(item, COTIZACION_FILE_COLUMN_ID)

                if cotizacion_url:
                    suffix = Path(cotizacion_url.split("?")[0]).suffix or ".xlsx"
                    cotizacion_path = str(output_directory / f"{stem}_cotizacion{suffix}")
                    download_file(cotizacion_url, cotizacion_path)
                    cotizacion_rows = parse_cotizacion_upload(cotizacion_path)
        except Exception as e:
            print(f"ERROR COTIZACION_UPLOAD: {e}")
            cotizacion_rows = []

        print("COTIZACION_ROWS =", cotizacion_rows)

        replacements["__COTIZACION_ROWS__"] = cotizacion_rows

        signature_path = None

        metodo_firma = (data.get("metodo_firma") or "").strip().lower()

        if metodo_firma == METODO_FIRMA_MONDAY_LABEL.strip().lower() and FIRMA_MONDAY_COLUMN_ID:
            firma_column_id = FIRMA_MONDAY_COLUMN_ID
        else:
            firma_column_id = SIGNATURE_COLUMN_ID

        print(f"METODO_FIRMA = {metodo_firma!r} -> columna {firma_column_id}")

        try:
            signature_url = get_file_public_url(item, firma_column_id)

            if signature_url:
                suffix = Path(signature_url.split("?")[0]).suffix or ".png"
                signature_path = str(output_directory / f"{stem}_firma{suffix}")
                download_file(signature_url, signature_path)
        except Exception as e:
            print(f"ERROR FIRMA: {e}")
            signature_path = None

        replacements["__SIGNATURE_PATH__"] = signature_path

        render_excel(base / ACTA_TEMPLATE, xlsx, replacements)

        upload_file(item_id, ACTA_XLSX_COLUMN_ID, xlsx)

        change_status(item_id, board_id, ACTA_STATUS_COLUMN_ID, "Generado")

        try:
            start_gerente_signing(item_id, board_id)
        except Exception as e:
            print(f"GERENTE_FIRMA: no se pudo iniciar el flujo de firma: {e}")

        return {"xlsx": xlsx, "name": stem}

    except Exception:
        try:
            change_status(item_id, board_id, ACTA_STATUS_COLUMN_ID, "Error")
        finally:
            raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("item_id")
    args = parser.parse_args()

    print(generate_acta(args.item_id))
