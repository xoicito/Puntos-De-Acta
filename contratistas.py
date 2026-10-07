import difflib
import re
import unicodedata

from config import (
    ACTA_CONTRATISTA_COLUMN_ID,
    COLUMN_ALIASES,
    CONTRATISTA_DB_BOARD_ID,
    CONTRATISTA_DB_COLUMNS,
)
from utils.monday_client import create_update, list_board_items, update_text_column


class ContratistaNoEncontrado(Exception):
    """El contratista elegido en el formulario no existe en la base de datos."""


def _norm(text):
    text = unicodedata.normalize("NFD", str(text or ""))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def _texto(item, column_id):
    for c in item.get("column_values", []):
        if c["id"] == column_id:
            return (c.get("text") or "").strip()

    return ""


def buscar_contratista(nombre, catalogo=None):
    """Datos del contratista `nombre` en la Base de Datos de Contratistas, como
    {"empresa", "nit", "contacto", ...} (solo lo que tenga valor), o None si no
    existe. La coincidencia ignora mayusculas, tildes, puntuacion y espacios:
    el nombre sale de una lista desplegable cuyas etiquetas son los nombres de
    la base de datos, asi que debe ser el mismo salvo esas diferencias."""

    columnas = [c for c in CONTRATISTA_DB_COLUMNS.values() if c]
    catalogo = catalogo if catalogo is not None else list_board_items(CONTRATISTA_DB_BOARD_ID, columnas)
    objetivo = _norm(nombre)

    for it in catalogo:
        if _norm(it.get("name")) != objetivo:
            continue

        datos = {"empresa": it["name"].strip()}

        for campo, column_id in CONTRATISTA_DB_COLUMNS.items():
            valor = (it.get("columns", {}).get(column_id) or "").strip() if column_id else ""

            if valor:
                datos[campo] = valor

        return datos

    return None


def sugerencias(nombre, catalogo, n=3):
    nombres = [it.get("name", "") for it in catalogo]
    objetivo = _norm(nombre)

    return sorted(nombres, key=lambda c: -difflib.SequenceMatcher(None, objetivo, _norm(c)).ratio())[:n]


def aplicar_contratista(item_id, data, catalogo=None):
    """Si el formulario trae un contratista elegido de la lista, sus datos de la
    base de datos reemplazan a los escritos a mano (empresa, NIT, contacto,
    telefono, correo, RTU - los que la base tenga). Sin contratista elegido (o
    con la funcion apagada) devuelve `data` tal cual. Si el nombre no esta en
    la base, avisa en el item y lanza ContratistaNoEncontrado."""

    if not ACTA_CONTRATISTA_COLUMN_ID:
        return data

    nombre = (data.get("contratista_db") or "").strip()

    if not nombre:
        return data

    columnas = [c for c in CONTRATISTA_DB_COLUMNS.values() if c]
    catalogo = catalogo if catalogo is not None else list_board_items(CONTRATISTA_DB_BOARD_ID, columnas)
    datos = buscar_contratista(nombre, catalogo)

    if datos is None:
        parecidos = ", ".join(sugerencias(nombre, catalogo))

        try:
            create_update(
                item_id,
                f"No se genero el Punto de Acta: el contratista '{nombre}' no se encontro en la "
                f"Base de Datos de Contratistas. Nombres parecidos: {parecidos}. Si es un contratista nuevo, "
                "agregalo primero a la base de datos y a la lista del formulario.",
            )
        except Exception as e:
            print(f"ERROR_CONTRATISTA_FLAG: {e}")

        raise ContratistaNoEncontrado(f"Contratista '{nombre}' no esta en la base de datos")

    data = dict(data)
    data.update(datos)
    print(f"CONTRATISTA_DB: '{nombre}' -> {sorted(datos)}")

    return data


def escribir_en_item(item_id, board_id, original, nuevo):
    """Escribe en las columnas del item los datos que vinieron de la base de
    datos. Asi el resto del sistema (Control de Facturas, Procurement, etc.),
    que lee empresa / NIT / contacto... directo de esas columnas, sigue
    funcionando aunque el formulario ya no las pregunte. Solo toca lo que
    cambio; un fallo en una columna no detiene a las demas."""

    for campo in ("empresa", "nit", "contacto", "telefono", "correo", "rtu"):
        valor = (nuevo.get(campo) or "").strip()

        if not valor or valor == (original.get(campo) or "").strip():
            continue

        columnas = COLUMN_ALIASES.get(campo) or []

        if not columnas:
            continue

        try:
            update_text_column(item_id, board_id, columnas[0], valor)
        except Exception as e:
            print(f"CONTRATISTA_DB: no se pudo escribir {campo} en el item {item_id}: {e}")
