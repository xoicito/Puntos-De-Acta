import json
import re
from pathlib import Path

from config import (
    ACTA_BOARD_ID,
    ACTA_OUTPUT_DIR,
    ACTA_STATUS_COLUMN_ID,
    ACTA_TEMPLATE,
    ACTA_XLSX_COLUMN_ID,
)
from utils.monday_client import change_status, get_item, upload_file
from utils.acta_builder import build_blocks, display_date, item_data, pct
from utils.excel_writer import render_excel


def _clean(value):
    return re.sub(r"[^A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ._-]+", "_", str(value or "")).strip("_")


def generate_acta(item_id):
    item = get_item(item_id)
    data = item_data(item)

    board_id = int(data.get("board_id") or ACTA_BOARD_ID)

    change_status(item_id, board_id, ACTA_STATUS_COLUMN_ID, "Procesando")

    try:
        base = Path(__file__).resolve().parent

        rubrics = json.loads((base / "rubros.json").read_text(encoding="utf-8"))

        replacements = {
            "{{PROYECTO}}": data["proyecto"],
            "{{RUBRO}}": data["rubro"],
            "{{NO_CONTRATO}}": data["no_contrato"],
            "{{TIPO_CONTRATO}}": data["tipo_contrato"],
            "{{FECHA_ACTA}}": display_date(data["fecha_acta"]),
            "{{EMPRESA}}": data["empresa"],
            "{{CONTACTO}}": data["contacto"],
            "{{TELEFONO}}": data["telefono"],
            "{{NIT}}": data["nit"],
            "{{NO_COTIZACION}}": data["no_cotizacion"],
            "{{ANTICIPO}}": pct(data["anticipo"]),
            "{{ESTIMACIONES}}": pct(data["estimaciones"]),
            "{{CONTRA_ENTREGA}}": pct(data["contra_entrega"]),
            "{{RETENIDO}}": pct(data["retenido"]),
        }

        replacements.update(build_blocks(data, rubrics))

        missing = [f for f in ("proyecto", "rubro", "no_contrato", "empresa") if not data.get(f)]

        if missing:
            raise ValueError("Campos obligatorios vacíos: " + ", ".join(missing))

        stem = _clean(f"PA-{data['no_contrato']}-{data['rubro']}-{data['proyecto']}")[:140]

        output_directory = Path(ACTA_OUTPUT_DIR)
        output_directory.mkdir(parents=True, exist_ok=True)

        xlsx = str(output_directory / f"{stem}.xlsx")

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
