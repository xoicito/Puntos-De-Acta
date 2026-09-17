from pathlib import Path

from openpyxl import load_workbook

from config import (
    ACTA_OUTPUT_DIR,
    FIRMA_PA_EDITABLE_COLUMN_ID,
    FIRMA_PA_FIRMADO_COLUMN_ID,
    MELISSA_SIGNATURE_PATH,
)
from utils.monday_client import (
    download_file,
    get_file_public_url,
    get_item,
    upload_file,
)
from utils.excel_writer import insert_signature


def sign_document(item_id):
    item = get_item(item_id)

    editable_url = get_file_public_url(item, FIRMA_PA_EDITABLE_COLUMN_ID)

    if not editable_url:
        raise ValueError(
            f"El item {item_id} no tiene archivo en la columna PA EDITABLE"
        )

    base = Path(__file__).resolve().parent

    output_directory = Path(ACTA_OUTPUT_DIR)
    output_directory.mkdir(parents=True, exist_ok=True)

    suffix = Path(editable_url.split("?")[0]).suffix or ".xlsx"
    source_path = str(output_directory / f"PA_EDITABLE_{item_id}{suffix}")

    download_file(editable_url, source_path)

    wb = load_workbook(source_path)
    ws = wb["C-9-12"] if "C-9-12" in wb.sheetnames else wb.active

    signed_ok = insert_signature(
        ws,
        str(base / MELISSA_SIGNATURE_PATH),
        top_left="L128",
        cols=("L", "M"),
        rows=(128, 129, 130, 131),
    )

    if not signed_ok:
        raise RuntimeError(
            f"No se pudo insertar la firma en el item {item_id}; "
            "no se sube el archivo a PA FIRMADO PRC"
        )

    signed_path = str(output_directory / f"PA_FIRMADO_{item_id}.xlsx")
    wb.save(signed_path)

    upload_file(item_id, FIRMA_PA_FIRMADO_COLUMN_ID, signed_path)

    return {"signed": signed_path}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("item_id")
    args = parser.parse_args()

    print(sign_document(args.item_id))
