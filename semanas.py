import threading
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from utils.monday_client import create_group, list_board_items, list_groups, move_item_to_group

GUATEMALA_TZ = ZoneInfo("America/Guatemala")

MESES = [
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
    "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE",
]

_group_lock = threading.Lock()


def parse_fecha(text):
    """Monday's created_at ("2026-10-02T15:04:05Z") -> aware datetime."""
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _local(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(GUATEMALA_TZ)


def es_solicitud_tardia(dt):
    """Politica de Aprobacion de Puntos de Acta: se reciben de lunes 7:00 a.m.
    a miercoles 10:00 a.m. (hora de Guatemala); todo lo demas pasa al
    siguiente ciclo."""

    dt = _local(dt)
    weekday = dt.weekday()  # lunes=0

    if weekday == 0:
        return dt.hour < 7
    if weekday == 1:
        return False
    if weekday == 2:
        return (dt.hour, dt.minute, dt.second) > (10, 0, 0)

    return True


def ventana_semanal(dt):
    """Una semana va de miercoles 10:01 a.m. a miercoles 10:00 a.m. Devuelve
    (inicio, fin) de la ventana que contiene a dt - el fin es el miercoles
    10:00 a.m. (inclusive)."""

    dt = _local(dt)
    miercoles = (dt - timedelta(days=dt.weekday() - 2)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    fin = miercoles if dt <= miercoles else miercoles + timedelta(days=7)

    return fin - timedelta(days=7), fin


def titulo_semana(dt):
    inicio, fin = ventana_semanal(dt)

    return (
        f"SEMANA DEL {inicio.day} DE {MESES[inicio.month - 1]} "
        f"AL {fin.day} DE {MESES[fin.month - 1]} DE {fin.year}"
    )


def fecha_liberacion(creado):
    """Para una solicitud tardia: el primer lunes a las 8:00 a.m. (hora de
    Guatemala) a partir de su ingreso - ahi aparece en el board de Melissa."""

    dt = _local(creado)
    candidato = (dt + timedelta(days=(0 - dt.weekday()) % 7)).replace(
        hour=8, minute=0, second=0, microsecond=0
    )

    if candidato < dt:
        candidato += timedelta(days=7)

    return candidato


def asignar_grupo_semanal(item_id, board_id, ahora=None):
    """Mueve el item recien creado al grupo de su semana (miercoles a
    miercoles), creandolo arriba del todo si todavia no existe."""

    title = titulo_semana(ahora or datetime.now(GUATEMALA_TZ))

    with _group_lock:
        group_id = next(
            (g["id"] for g in list_groups(board_id) if g["title"].strip().lower() == title.lower()),
            None,
        ) or create_group(board_id, title, at_top=True)

    move_item_to_group(item_id, group_id)


def agrupar_semana_actual(board_id, ahora=None):
    """Red de seguridad que corre en el cron diario (y se puede lanzar a
    mano): cualquier item del board creado dentro de la semana en curso
    (miercoles 10:01 a miercoles 10:00) que no este en el grupo de esa semana
    se mueve ahi. Solo mira la semana actual - lo anterior no se toca, asi que
    los grupos viejos quedan como estan. Devuelve cuantos movio."""

    ahora = ahora or datetime.now(GUATEMALA_TZ)
    inicio, fin = ventana_semanal(ahora)
    title = titulo_semana(ahora)

    items = list_board_items(board_id, [])
    pendientes = []

    for it in items:
        if not it.get("created_at"):
            continue

        creado = _local(parse_fecha(it["created_at"]))

        if inicio < creado <= fin:
            pendientes.append(it)

    if not pendientes:
        return 0

    with _group_lock:
        group_id = next(
            (g["id"] for g in list_groups(board_id) if g["title"].strip().lower() == title.lower()),
            None,
        ) or create_group(board_id, title, at_top=True)

    movidos = 0

    for it in pendientes:
        if it.get("group_id") == group_id:
            continue

        try:
            move_item_to_group(it["id"], group_id)
            movidos += 1
        except Exception as e:
            print(f"SEMANAS: item={it['id']} no se pudo mover: {e}", flush=True)

    print(f"SEMANAS: {movidos} items movidos a '{title}'", flush=True)

    return movidos
