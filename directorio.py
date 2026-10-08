"""Directorio de personas: un solo board con Lideres, Gerentes y PMO.

Cada fila es una persona: nombre (el nombre del item), correo, uno o varios
roles (Lider / Gerente / PMO), un estado de acceso (Pendiente / Aprobado /
Rechazado) y alias (otros nombres con los que aparece en los formularios).

Quien aprueba cambia el estado en Monday; el portal lo lee en cada inicio de
sesion. Sin DIRECTORIO_BOARD_ID el sistema sigue usando los boards separados de
Gerentes y de Lideres, como antes.
"""

import re
import threading
import time
import unicodedata

from config import (
    DIRECTORIO_ACCESO_COLUMN_ID,
    DIRECTORIO_ACCESO_TIPO,
    DIRECTORIO_ALIAS_COLUMN_ID,
    DIRECTORIO_BOARD_ID,
    DIRECTORIO_CORREO_COLUMN_ID,
    DIRECTORIO_ROL_COLUMN_ID,
    DIRECTORIO_ROL_SOLICITADO_COLUMN_ID,
)
from utils.monday_client import (
    change_multiple_column_values,
    create_item,
    create_update,
    list_board_items,
    update_text_column,
)

ROLES = ("lider", "gerente", "pmo")
ETIQUETA_ROL = {"lider": "Líder", "gerente": "Gerente", "pmo": "PMO"}

_cache = {"t": 0, "filas": None}
_lock = threading.Lock()
_TTL = 15


def activo():
    return bool(DIRECTORIO_BOARD_ID and DIRECTORIO_CORREO_COLUMN_ID and DIRECTORIO_ROL_COLUMN_ID)


def _norm(texto):
    t = unicodedata.normalize("NFD", str(texto or ""))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")

    return re.sub(r"[^a-z0-9]+", " ", t.casefold()).strip()


def _columnas():
    return [c for c in (DIRECTORIO_CORREO_COLUMN_ID, DIRECTORIO_ROL_COLUMN_ID, DIRECTORIO_ACCESO_COLUMN_ID,
                        DIRECTORIO_ALIAS_COLUMN_ID, DIRECTORIO_ROL_SOLICITADO_COLUMN_ID) if c]


def _roles(texto):
    """{'lider','gerente'} a partir de 'Líder, Gerente' (el texto de una columna de lista)."""

    encontrados = set()

    for parte in re.split(r"[,;/]", texto or ""):
        n = _norm(parte)

        if n.startswith("lider"):
            encontrados.add("lider")
        elif n.startswith("gerente"):
            encontrados.add("gerente")
        elif n.startswith("pmo"):
            encontrados.add("pmo")

    return encontrados


def _alias(texto):
    return [a.strip() for a in re.split(r"[,;\n]", texto or "") if a.strip()]


def _acceso(texto):
    """'aprobado' | 'pendiente' | 'rechazado'. Una fila sin estado cuenta como
    aprobada: asi las personas que ya estaban en la lista no necesitan nada mas."""

    n = _norm(texto)

    # Si por error quedan marcadas dos opciones (por ejemplo en una lista), manda
    # la mas restrictiva: nunca se concede acceso por una ambiguedad.
    if "rechaz" in n:
        return "rechazado"

    if "pendiente" in n:
        return "pendiente"

    return "aprobado"


def personas(forzar=False):
    """Todas las filas del directorio, ya interpretadas (cache corta)."""

    with _lock:
        if not forzar and _cache["filas"] is not None and time.time() - _cache["t"] < _TTL:
            return _cache["filas"]

    filas = []

    for it in list_board_items(DIRECTORIO_BOARD_ID, _columnas()):
        c = it["columns"]
        filas.append({
            "id": str(it["id"]),
            "nombre": (it.get("name") or "").strip(),
            "correo": (c.get(DIRECTORIO_CORREO_COLUMN_ID) or "").strip().lower(),
            "roles": _roles(c.get(DIRECTORIO_ROL_COLUMN_ID)),
            "acceso": _acceso(c.get(DIRECTORIO_ACCESO_COLUMN_ID)),
            "alias": _alias(c.get(DIRECTORIO_ALIAS_COLUMN_ID)),
            "solicitado": (c.get(DIRECTORIO_ROL_SOLICITADO_COLUMN_ID) or "").strip(),
        })

    if not filas:
        print(f"DIRECTORIO: el board {DIRECTORIO_BOARD_ID} devolvio 0 filas (el token del servidor no lo ve, o esta vacio)", flush=True)

    with _lock:
        _cache.update(t=time.time(), filas=filas)

    return filas


def persona_por_correo(correo, forzar=False):
    correo = (correo or "").strip().lower()

    return next((p for p in personas(forzar) if correo and p["correo"] == correo), None)


def roles_de(correo, forzar=True):
    """{'gerente': nombre | None, 'lider': nombre | None, 'estado': ...} para un
    correo. Solo cuentan los roles de una persona con acceso aprobado."""

    p = persona_por_correo(correo, forzar)

    if p is None:
        return {"gerente": None, "lider": None, "estado": "desconocido", "persona": None}

    if p["acceso"] != "aprobado" or not p["roles"]:
        return {"gerente": None, "lider": None, "estado": p["acceso"] if p["acceso"] != "aprobado" else "sin_rol", "persona": p}

    return {
        "gerente": p["nombre"] if "gerente" in p["roles"] else None,
        "lider": p["nombre"] if "lider" in p["roles"] else None,
        "estado": "aprobado",
        "persona": p,
    }


def buscar_correo(nombre, rol):
    """(nombre, correo) de la persona con ese rol cuyo nombre (o alias) es
    `nombre`; sirve para resolver el Gerente o el PMO que el lider eligio en el
    formulario. (None, None) si no existe o no tiene acceso aprobado."""

    objetivo = _norm(nombre)

    if not objetivo:
        return None, None

    for p in personas():
        if rol in p["roles"] and p["acceso"] == "aprobado" and objetivo in [_norm(p["nombre"])] + [_norm(a) for a in p["alias"]]:
            return p["nombre"], p["correo"] or None

    return None, None


def crear_solicitud(correo, nombre, roles_solicitados):
    """Fila nueva en el directorio con acceso Pendiente. El rol que se concede
    lo pone quien aprueba (columna Rol); lo que se pidio queda como comentario
    del item (y en la columna "Rol solicitado", si existe)."""

    if isinstance(roles_solicitados, str):
        roles_solicitados = [roles_solicitados]

    pedidos = ", ".join(ETIQUETA_ROL.get(r, r) for r in roles_solicitados)
    item_id = create_item(DIRECTORIO_BOARD_ID, nombre)
    valores = {DIRECTORIO_CORREO_COLUMN_ID: correo}

    if DIRECTORIO_ACCESO_COLUMN_ID:
        valores[DIRECTORIO_ACCESO_COLUMN_ID] = {
            "dropdown": {"labels": ["Pendiente"]},
            "text": "Pendiente",
        }.get(DIRECTORIO_ACCESO_TIPO, {"label": "Pendiente"})

    if DIRECTORIO_ROL_SOLICITADO_COLUMN_ID:
        valores[DIRECTORIO_ROL_SOLICITADO_COLUMN_ID] = pedidos

    change_multiple_column_values(item_id, DIRECTORIO_BOARD_ID, valores)

    try:
        create_update(
            item_id,
            f"<p><b>Solicitud de acceso al portal.</b></p>"
            f"<p>Cuenta de Monday: {correo}<br>Rol solicitado: <b>{pedidos}</b></p>"
            "<p>Para aprobarla: elija el <b>Rol</b> que corresponda en la columna Rol "
            "(puede ser distinto del solicitado) y cambie <b>Acceso</b> a «Aprobado». "
            "Para negarla, cambie Acceso a «Rechazado».</p>",
        )
    except Exception as e:
        print(f"DIRECTORIO: no se pudo dejar el comentario de la solicitud {item_id}: {e}", flush=True)

    personas(forzar=True)

    return item_id


def agregar_alias(item_id, alias):
    """Suma `alias` a la columna de alias de esa persona (sin repetir)."""

    if not DIRECTORIO_ALIAS_COLUMN_ID:
        raise RuntimeError("DIRECTORIO_ALIAS_COLUMN_ID no esta configurado")

    persona = next((p for p in personas(True) if p["id"] == str(item_id)), None)

    if persona is None:
        raise LookupError("La persona no existe en el directorio")

    existentes = persona["alias"]

    if _norm(alias) in [_norm(a) for a in existentes] + [_norm(persona["nombre"])]:
        return

    update_text_column(item_id, DIRECTORIO_BOARD_ID, DIRECTORIO_ALIAS_COLUMN_ID, ", ".join(existentes + [alias.strip()]))
    personas(forzar=True)
