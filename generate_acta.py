import json
import re
from pathlib import Path

from config import (
    ACTA_BOARD_ID,
    ACTA_ID_COLUMN_ID,
    ACTA_OUTPUT_DIR,
    ACTA_STATUS_COLUMN_ID,
    ACTA_TEMPLATE,
    ACTA_XLSX_COLUMN_ID,
    SIGNATURE_COLUMN_ID,
)
from utils.monday_client import (
    change_status,
    download_file,
    generate_acta_id,
    get_file_public_url,
    get_item,
    upload_file,
    get_cotizacion_rows,
    update_text_column,
)
from utils.acta_builder import build_blocks, display_date, item_data, pct
from utils.excel_writer import render_excel


def _clean(value):
    return re.sub(r"[^A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ._-]+", "_", str(value or "")).strip("_")


def generate_acta(item_id):
    item = get_item(item_id)
    data = item_data(item)

    board_id = int(data.get("board_id") or ACTA_BOARD_ID)

    if not data.get("acta_id"):
        data["acta_id"] = generate_acta_id()
        update_text_column(item_id, board_id, ACTA_ID_COLUMN_ID, data["acta_id"])

    print("ACTA_ID =", data.get("acta_id"))

    cotizacion_rows = get_cotizacion_rows(
        data.get("acta_id")
    )

    print(
        "COTIZACION_ROWS =",
        cotizacion_rows
    )
    print("PUNTOS_GENERALES:", data.get("puntos_generales"))
    print("PLANOS_ENTREGADOS:", data.get("planos_entregados"))
    print("MULTAS_APLICAR =", data.get("multas_aplicar"))

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

        replacements["__COTIZACION_ROWS__"] = (
            cotizacion_rows
        )

        missing = [f for f in ("proyecto", "rubro", "no_contrato", "empresa") if not data.get(f)]

        if missing:
            raise ValueError("Campos obligatorios vacíos: " + ", ".join(missing))

        stem = _clean(f"PA-{data['no_contrato']}-{data['rubro']}-{data['proyecto']}")[:140]

        output_directory = Path(ACTA_OUTPUT_DIR)
        output_directory.mkdir(parents=True, exist_ok=True)

        xlsx = str(output_directory / f"{stem}.xlsx")

        signature_path = None

        try:
            signature_url = get_file_public_url(item, SIGNATURE_COLUMN_ID)

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
