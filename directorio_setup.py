"""Crea de un solo jalon el board "Directorio de personas" en Monday y lo llena
con los Gerentes, PMO y Lideres que ya tienen (unidos por correo: una persona con
dos roles queda en UNA sola fila).

Uso (como create_rubro_columns.py: el token lo pones tu, no se comparte):
    1. Define MONDAY_TOKEN con el token real (variable de entorno).
    2. python directorio_setup.py                          -> solo muestra el plan
    3. python directorio_setup.py --aplicar                -> crea el board de verdad
    Opciones:
       --lideres lideres.csv   CSV con columnas nombre,correo (los lideres que no estan en Monday)
       --publico               el board se crea publico (por defecto es privado: tiene correos)
       --duenos a@x.com,b@x.com  quienes seran duenos del board y lo veran (recomendado: privado + duenos)
       --agregar-duenos ID --duenos ...   agrega duenos a un board ya creado
       --borrar ID             borra un board creado por este script (pide confirmacion)

Al terminar imprime las variables de entorno listas para pegar en Render.
Los boards viejos de Gerentes y PMO NO se tocan.
"""

import argparse
import csv
import re
import sys
import unicodedata

from config import (
    GERENTE_EMAIL_COLUMN_ID,
    GERENTES_BOARD_ID,
    LIDERES_BOARD_ID,
    LIDERES_EMAIL_COLUMN_ID,
    PMO_BOARD_ID,
    PMO_EMAIL_COLUMN_ID,
)

NOMBRE_BOARD = "Directorio de personas"
ROLES = ["Líder", "Gerente", "PMO"]
ACCESOS = ["Pendiente", "Aprobado", "Rechazado"]


def _norm(texto):
    t = unicodedata.normalize("NFD", str(texto or ""))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")

    return re.sub(r"[^a-z0-9]+", " ", t.casefold()).strip()


def fusionar(gerentes, pmos, lideres):
    """Une las tres listas [(nombre, correo)] en personas unicas.

    Dos filas son la misma persona si comparten correo (o, sin correo, el mismo
    nombre). Gana el primer nombre visto (Gerentes, luego PMO, luego Lideres); los
    demas nombres con que aparece quedan como alias, para que el formulario los
    reconozca. Devuelve (personas, avisos)."""

    por_clave, avisos = {}, []

    for rol, filas in (("Gerente", gerentes), ("PMO", pmos), ("Líder", lideres)):
        for nombre, correo in filas:
            nombre = " ".join((nombre or "").split())
            correo = (correo or "").strip().lower()

            if not nombre:
                continue

            clave = correo or "nombre:" + _norm(nombre)
            p = por_clave.setdefault(clave, {"nombre": nombre, "correo": correo, "roles": [], "alias": []})

            if rol not in p["roles"]:
                p["roles"].append(rol)

            if _norm(nombre) != _norm(p["nombre"]) and nombre not in p["alias"]:
                p["alias"].append(nombre)

    personas = sorted(por_clave.values(), key=lambda p: _norm(p["nombre"]))

    for p in personas:
        p["roles"].sort(key=ROLES.index)

        if not p["correo"]:
            avisos.append(f"{p['nombre']} ({', '.join(p['roles'])}) no tiene correo: no podrá iniciar sesión hasta que se lo agreguen.")

    return personas, avisos


def _leer_board(board_id, columna_correo):
    from utils.monday_client import list_board_items

    return [(it.get("name", ""), it["columns"].get(columna_correo, "")) for it in list_board_items(board_id, [columna_correo])]


def _leer_csv(ruta):
    filas = []

    with open(ruta, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            r = {_norm(k): (v or "") for k, v in r.items()}
            filas.append((r.get("nombre") or r.get("name") or r.get("nombre completo") or "", r.get("correo") or r.get("email") or r.get("e mail") or ""))

    return filas


def _mostrar(personas, avisos):
    print(f"\nPersonas que irían al directorio: {len(personas)}")
    print(f"{'Nombre':38} {'Correo':34} Roles")
    print("-" * 92)

    for p in personas:
        extra = f"   (alias: {', '.join(p['alias'])})" if p["alias"] else ""
        print(f"{p['nombre'][:37]:38} {(p['correo'] or '(sin correo)')[:33]:34} {', '.join(p['roles'])}{extra}")

    if avisos:
        print("\nAvisos:")

        for a in avisos:
            print(f"  - {a}")


def _agregar_duenos(board, correos):
    """Agrega a esas personas como dueñas del board (para que lo vean aunque sea
    privado). Avisa de los correos que no son usuarios de Monday."""

    from utils.monday_client import add_board_owners, find_user_ids

    correos = [c.strip().lower() for c in correos if c.strip()]
    ids = find_user_ids(correos)

    for c in correos:
        if c not in ids:
            print(f"  (no encontré un usuario de Monday con el correo {c}; no se agregó)")

    if ids:
        add_board_owners(board, list(ids.values()))
        print(f"  Dueños agregados al board {board}: {', '.join(ids)}")


def _borrar(board_id):
    """Borra un board creado por este script. Solo si se llama como el que crea
    el script, y pidiendo confirmacion escrita."""

    from utils.monday_client import delete_board, get_board_name

    nombre = get_board_name(board_id)

    if nombre is None:
        sys.exit(f"Con este token no veo ningún board con id {board_id}. Puede ser privado de otra cuenta: bórrelo desde la cuenta que lo creó.")

    if nombre != NOMBRE_BOARD:
        sys.exit(f'El board {board_id} se llama "{nombre}", no "{NOMBRE_BOARD}". Por seguridad no se borra.')

    if input(f'Se va a BORRAR el board "{nombre}" ({board_id}). Escriba BORRAR para confirmar: ').strip() != "BORRAR":
        sys.exit("Cancelado: no se borró nada.")

    delete_board(board_id)
    print("Board borrado.")


def _crear_lista(board, titulo, etiquetas):
    """Crea una columna de lista con esas opciones y COMPRUEBA que Monday las creo
    (una vez creo la columna vacia y todo fallo despues). Prueba las formas conocidas
    de pedirlas; si ninguna funciona, deja una columna de texto. Devuelve (id, tipo)
    con tipo "dropdown" o "text"."""

    from utils.monday_client import create_column_tipo, delete_column, get_status_label_map

    intentos = [
        {"settings": {"labels": [{"id": i, "label": e} for i, e in enumerate(etiquetas, 1)]}},
        {"labels": etiquetas},
        {"labels": {str(i): e for i, e in enumerate(etiquetas, 1)}},
    ]

    for defaults in intentos:
        try:
            col = create_column_tipo(board, titulo, "dropdown", defaults)
        except Exception as e:
            print(f"  ({titulo}: Monday rechazó una forma de crear la lista: {str(e)[:90]})")
            continue

        creadas = set(get_status_label_map(board, col).values())

        if set(etiquetas) <= creadas:
            return col, "dropdown"

        delete_column(board, col)  # quedo vacia: se borra y se prueba la siguiente forma

    print(f"  ({titulo}: Monday no creó las opciones de la lista; se usa una columna de texto.)")

    return create_column_tipo(board, titulo, "text"), "text"


def _crear(personas, publico, duenos=()):
    import json

    from utils.monday_client import (
        change_multiple_column_values,
        create_board,
        create_column_tipo,
        create_item,
        find_board_by_name,
        get_status_label_map,
    )

    if find_board_by_name(NOMBRE_BOARD):
        sys.exit(f'Ya existe un board llamado "{NOMBRE_BOARD}". Para no duplicarlo, no se creó nada. Bórrelo o renómbrelo y vuelva a correr el script.')

    board = create_board(NOMBRE_BOARD, "public" if publico else "private")
    print(f"\nBoard creado: {board}")

    try:
        _agregar_duenos(board, duenos)
        _llenar(board, personas)
    except Exception:
        print(f"\nALGO FALLÓ. El board {board} quedó a medias: bórrelo en Monday y vuelva a correr el script.")
        raise


def _llenar(board, personas):
    from utils.monday_client import (
        change_multiple_column_values,
        create_column_tipo,
        create_item,
        get_status_label_map,
    )

    col_correo = create_column_tipo(board, "Correo", "text")
    col_rol, tipo_rol = _crear_lista(board, "Rol", ROLES)      # lista con varias opciones (una persona puede tener dos roles)
    col_alias = create_column_tipo(board, "Alias", "text")
    col_solicitado = create_column_tipo(board, "Rol solicitado", "text")

    # "Acceso": primero como estado con colores; si Monday no crea las etiquetas, como lista.
    tipo_acceso = "status"
    col_acceso = create_column_tipo(board, "Acceso", "status", {"labels": {str(i): t for i, t in enumerate(ACCESOS)}})
    existentes = {t for t in get_status_label_map(board, col_acceso).values()}

    if not set(ACCESOS) <= existentes:
        print("  (Monday no creó las etiquetas del estado; se usa una lista en su lugar.)")
        from utils.monday_client import delete_column

        delete_column(board, col_acceso)
        col_acceso, tipo_acceso = _crear_lista(board, "Acceso", ACCESOS)

    for i, p in enumerate(personas, 1):
        item = create_item(board, p["nombre"])
        valores = {col_correo: p["correo"], col_rol: ({"labels": p["roles"]} if tipo_rol == "dropdown" else ", ".join(p["roles"]))}

        if p["alias"]:
            valores[col_alias] = ", ".join(p["alias"])

        change_multiple_column_values(item, board, valores)
        print(f"  {i}/{len(personas)} {p['nombre']}")

    print("\n" + "=" * 70)
    print("Listo. Pega estas variables en Render (Environment):\n")
    print(f"DIRECTORIO_BOARD_ID={board}")
    print(f"DIRECTORIO_CORREO_COLUMN_ID={col_correo}")
    print(f"DIRECTORIO_ROL_COLUMN_ID={col_rol}")
    print(f"DIRECTORIO_ACCESO_COLUMN_ID={col_acceso}")
    print(f"DIRECTORIO_ACCESO_TIPO={'dropdown' if tipo_acceso == 'dropdown' else 'status' if tipo_acceso == 'status' else 'text'}")
    print(f"DIRECTORIO_ALIAS_COLUMN_ID={col_alias}")
    print(f"DIRECTORIO_ROL_SOLICITADO_COLUMN_ID={col_solicitado}")
    print("PORTAL_ADMIN_CORREOS=tu.correo@...   (separados por coma)")
    print("=" * 70)
    if tipo_rol == "text":
        print("\nOJO: la columna Rol quedó como texto. Al aprobar a alguien escriba sus roles separados por coma (Líder, Gerente).")

    if tipo_acceso == "text":
        print("OJO: la columna Acceso quedó como texto. Escriba Pendiente / Aprobado / Rechazado.")

    print("\nLos Acceso de las filas quedan VACIOS a propósito: una fila sin estado cuenta como aprobada.")
    print("Las solicitudes nuevas llegarán como «Pendiente»; las apruebas cambiando Acceso a «Aprobado».")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--aplicar", action="store_true", help="crear el board de verdad (sin esto solo se muestra el plan)")
    ap.add_argument("--lideres", help="CSV con columnas nombre,correo")
    ap.add_argument("--publico", action="store_true", help="crear el board como público")
    ap.add_argument("--duenos", help="correos (separados por coma) de quienes serán dueños del board y lo verán")
    ap.add_argument("--borrar", metavar="ID", help="borra un board creado por este script (pide confirmación)")
    ap.add_argument("--agregar-duenos", metavar="ID", help="solo agrega los --duenos a un board que ya existe")
    args = ap.parse_args()

    if args.borrar:
        _borrar(args.borrar)
        return

    if args.agregar_duenos:
        if not args.duenos:
            sys.exit("Falta --duenos con los correos.")

        _agregar_duenos(args.agregar_duenos, args.duenos.split(","))
        return

    gerentes = _leer_board(GERENTES_BOARD_ID, GERENTE_EMAIL_COLUMN_ID)
    pmos = _leer_board(PMO_BOARD_ID, PMO_EMAIL_COLUMN_ID)
    lideres = []

    if LIDERES_BOARD_ID and LIDERES_EMAIL_COLUMN_ID:
        lideres += _leer_board(LIDERES_BOARD_ID, LIDERES_EMAIL_COLUMN_ID)

    if args.lideres:
        lideres += _leer_csv(args.lideres)

    print(f"Leídos: {len(gerentes)} Gerentes, {len(pmos)} PMO, {len(lideres)} Líderes")
    personas, avisos = fusionar(gerentes, pmos, lideres)
    _mostrar(personas, avisos)

    if not args.aplicar:
        print("\nEsto es solo la vista previa: no se creó nada. Si todo está bien, corra de nuevo con --aplicar.")
        return

    _crear(personas, args.publico, (args.duenos or "").split(","))


if __name__ == "__main__":
    main()
