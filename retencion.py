from datetime import datetime, timezone
from pathlib import Path

from config import (
    ACTA_BOARD_ID,
    ACTA_OUTPUT_DIR,
    ACTA_PROCUREMENT_COLUMN_ID,
    ACTA_PROCUREMENT_ENVIADO_LABEL,
    ACTA_PROCUREMENT_ESPERA_LABEL,
    ACTA_XLSX_COLUMN_ID,
)
from firma_gerente import _send_to_procurement
from semanas import fecha_liberacion, parse_fecha
from utils.acta_builder import item_data
from utils.monday_client import (
    change_status,
    create_update,
    download_file,
    get_file_public_urls,
    get_item,
    list_board_items,
)


def _archivo_firmado(item):
    """Entre los archivos de la columna del acta, el firmado por el Gerente
    (lo sube apply_gerente_signature como *_firmado.xlsx); si no se
    reconoce por nombre, el ultimo que se subio."""

    files = get_file_public_urls(item, ACTA_XLSX_COLUMN_ID)

    if not files:
        return None

    for name, url in files:
        if "_firmado" in name.lower():
            return url

    return files[-1][1]


def liberar_retenidos():
    """Corre en el mismo cron diario que el escalamiento. Pasa a Procurement
    los Puntos de Acta que quedaron "En espera" y cuyo lunes de las 8:00 a.m.
    ya llego. Devuelve cuantos libero."""

    if not ACTA_PROCUREMENT_COLUMN_ID:
        return 0

    ahora = datetime.now(timezone.utc)
    items = list_board_items(ACTA_BOARD_ID, [ACTA_PROCUREMENT_COLUMN_ID])
    liberados = 0

    for it in items:
        if it["columns"].get(ACTA_PROCUREMENT_COLUMN_ID) != ACTA_PROCUREMENT_ESPERA_LABEL:
            continue

        if not it.get("created_at") or ahora < fecha_liberacion(parse_fecha(it["created_at"])):
            continue

        try:
            item = get_item(it["id"])
            url = _archivo_firmado(item)

            if not url:
                raise ValueError("no se encontro el archivo firmado en la columna del acta")

            output_directory = Path(ACTA_OUTPUT_DIR)
            output_directory.mkdir(parents=True, exist_ok=True)
            path = str(output_directory / f"liberado_{it['id']}.xlsx")
            download_file(url, path)

            _send_to_procurement(it["id"], item, path, item_data(item))
            change_status(it["id"], ACTA_BOARD_ID, ACTA_PROCUREMENT_COLUMN_ID, ACTA_PROCUREMENT_ENVIADO_LABEL)

            try:
                create_update(it["id"], "Liberado: el Punto de Acta ya aparece en el board de Procurement.")
            except Exception as e:
                print(f"RETENCION: item={it['id']} no se pudo publicar el aviso: {e}")

            print(f"RETENCION: item={it['id']} liberado a Procurement")
            liberados += 1
        except Exception as e:
            print(f"RETENCION: item={it['id']} no se pudo liberar: {e}")

    return liberados
