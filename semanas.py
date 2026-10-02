import threading
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from utils.monday_client import create_group, list_groups, move_item_to_group

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
