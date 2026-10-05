from config import FIRMA_BOARD_ID, FIRMA_ESTADO_COLUMN_ID
from control_facturas import _norm
from utils.monday_client import create_group, list_board_items, list_groups, move_item_to_group

GRUPO_FIRMADOS = "FIRMADOS"
GRUPO_RECHAZADOS = "RECHAZADOS"
GRUPO_ORIGEN = "POR REVISAR"


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
    los RECHAZADO al grupo RECHAZADOS. Los pendientes no se tocan, ni lo que ya esta en otro grupo."""

    items = list_board_items(FIRMA_BOARD_ID, [FIRMA_ESTADO_COLUMN_ID])
    groups = list_groups(FIRMA_BOARD_ID)

    # Solo se toca lo que sigue en POR REVISAR: lo que ya esta en otro grupo
    # (FIRMADOS, PASADOS, etc.) se queda donde esta.
    origen = [g["id"] for g in groups if _norm(g["title"]) == _norm(GRUPO_ORIGEN)]

    if not origen:
        raise ValueError(f"no existe el grupo '{GRUPO_ORIGEN}' en el board")
    destinos = {}
    resultado = {"firmados": 0, "rechazados": 0, "errores": 0}

    for it in items:
        if it.get("group_id") not in origen:
            continue

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


def movimientos_recientes(minutos=240):
    """Solo lectura: movimientos de items entre grupos en el board de Melissa
    durante los ultimos `minutos`, segun el activity log de Monday (para
    revisar o deshacer un reordenamiento)."""

    from datetime import datetime, timedelta, timezone

    from utils.monday_client import graphql

    ahora = datetime.now(timezone.utc)
    desde = (ahora - timedelta(minutes=minutos)).strftime("%Y-%m-%dT%H:%M:%SZ")
    hasta = (ahora + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")

    q = """query ($board: [ID!]!, $from: ISO8601DateTime, $to: ISO8601DateTime) {
        boards(ids: $board) {
            activity_logs(from: $from, to: $to, limit: 1000) { event data created_at }
        }
    }"""

    data = graphql(q, {"board": [str(FIRMA_BOARD_ID)], "from": desde, "to": hasta})
    logs = data["boards"][0]["activity_logs"] if data["boards"] else []

    return [l for l in logs if "group" in (l.get("event") or "")]


def mover_a_pasados(item_ids):
    """Devuelve los items indicados al grupo PASADOS."""

    destino = [g["id"] for g in list_groups(FIRMA_BOARD_ID) if _norm(g["title"]).startswith("pasados")]

    if not destino:
        raise ValueError("no existe un grupo PASADOS")

    for item_id in item_ids:
        move_item_to_group(item_id, destino[0])

    return len(item_ids)
