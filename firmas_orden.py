from config import FIRMA_BOARD_ID, FIRMA_ESTADO_COLUMN_ID
from control_facturas import _norm
from utils.monday_client import create_group, list_board_items, list_groups, move_item_to_group

GRUPO_FIRMADOS = "FIRMADOS"
GRUPO_RECHAZADOS = "RECHAZADOS"


def _grupo(groups, titulo):
    """Id del grupo cuyo titulo equivale a `titulo` (sin importar mayusculas,
    tildes ni singular/plural); si no existe se crea al final."""

    wanted = _norm(titulo).rstrip("s")

    for g in groups:
        if _norm(g["title"]).rstrip("s") == wanted:
            return g["id"]

    new_id = create_group(FIRMA_BOARD_ID, titulo)
    groups.append({"id": new_id, "title": titulo})

    return new_id


def ordenar_firmas():
    """Corre el domingo por la noche (cron externo). En el board de Melissa,
    todo Punto de Acta cuyo estado de aprobacion sea FIRMADO (cualquiera de
    sus variantes: SIN CONTRATO, LEGAL, FASTTRACK...) pasa al grupo FIRMADOS y
    los RECHAZADO al grupo RECHAZADOS. Los pendientes no se tocan."""

    items = list_board_items(FIRMA_BOARD_ID, [FIRMA_ESTADO_COLUMN_ID])
    groups = list_groups(FIRMA_BOARD_ID)
    destinos = {}
    resultado = {"firmados": 0, "rechazados": 0, "errores": 0}

    for it in items:
        estado = _norm(it["columns"].get(FIRMA_ESTADO_COLUMN_ID, ""))

        if estado.startswith("firmado"):
            clave, titulo = "firmados", GRUPO_FIRMADOS
        elif estado.startswith("rechazad"):
            clave, titulo = "rechazados", GRUPO_RECHAZADOS
        else:
            continue

        try:
            if titulo not in destinos:
                destinos[titulo] = _grupo(groups, titulo)

            if it.get("group_id") == destinos[titulo]:
                continue

            move_item_to_group(it["id"], destinos[titulo])
            resultado[clave] += 1
        except Exception as e:
            print(f"ORDEN_FIRMAS: item={it['id']} no se pudo mover: {e}", flush=True)
            resultado["errores"] += 1

    print(f"ORDEN_FIRMAS: {resultado}", flush=True)

    return resultado
