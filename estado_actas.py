"""Estado de cada Punto de Acta para la pestana "Estado de las actas" del portal.

Arma, para el Gerente o el Lider que inicio sesion, la lista de sus actas con:
en que paso del proceso van, si algo fallo o va a fallar (alertas con su causa y
que hacer) y como se ve en pantalla. La logica de derivar el estado esta separada
de las llamadas a Monday para poder probarla con datos de ejemplo.
"""

import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime, timedelta, timezone

import directorio
import identidad
from avisos import MARCA, TITULOS
from config import (
    ACTA_BOARD_ID,
    ACTA_ENVIAR_GERENTE_COLUMN_ID,
    ACTA_PROCUREMENT_COLUMN_ID,
    ACTA_PROCUREMENT_ESPERA_LABEL,
    ACTA_STATUS_COLUMN_ID,
    ACTA_XLSX_COLUMN_ID,
    COLUMN_ALIASES,
    FIRMA_BOARD_ID,
    FIRMA_ESTADO_COLUMN_ID,
    FIRMA_PA_ITEM_ID_COLUMN_ID,
    GERENTE_EMAIL_LINK_COLUMN_ID,
    GERENTE_FIRMA_ESTADO_COLUMN_ID,
    GERENTE_FIRMA_ESTADO_PENDIENTE,
)
from semanas import GUATEMALA_TZ, fecha_liberacion, parse_fecha
from utils.acta_builder import display_date
from utils.monday_client import get_item, get_item_updates, list_board_items

PASOS = ["Generada", "Enviada al Gerente", "Firmada por el Gerente", "En aprobación", "Aprobada"]

MINUTOS_ATASCADA = 10  # minutos en "Procesando" antes de considerarla atascada
DIAS_VENTANA = 45   # actas ya completadas mas viejas que esto ya no se muestran
DIAS_DUPLICADO = 7

_SEVERIDAD = {"error": 3, "aviso": 2, "curso": 1, "ok": 0}

# Motivos conocidos de rechazo / error al generar, reconocidos por palabras del
# comentario que el sistema deja en el item.
_MOTIVOS = [
    (("plantilla solicitada", "plantilla de alcance"),
     "La cotización no es la plantilla oficial",
     "Descargue la plantilla oficial, llénela con sus renglones y vuelva a llenar el formulario con ella."),
    (("porcentajes de forma de pago", "no suman 100"),
     "La forma de pago no suma 100 %",
     "Corrija los porcentajes en el formulario para que sumen 100 % y vuelva a generar el acta."),
    (("no se encontro en la base de datos", "base de datos de contratistas"),
     "El contratista no está en la base de datos",
     "Pida el alta del contratista y vuelva a generar el acta."),
    (("campos obligatorios",),
     "Faltan datos obligatorios del formulario",
     "Complete los datos que faltan y vuelva a generar el acta."),
]


def _norm(texto):
    t = unicodedata.normalize("NFD", str(texto or ""))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")

    return re.sub(r"[^a-z0-9]+", " ", t.casefold()).strip()


def _alias_ids(*campos):
    ids = []

    for campo in campos:
        ids.extend(c for c in COLUMN_ALIASES.get(campo, []) if c)

    return ids


COLUMNAS_ACTA = [
    c for c in (
        [ACTA_STATUS_COLUMN_ID, ACTA_ENVIAR_GERENTE_COLUMN_ID, GERENTE_FIRMA_ESTADO_COLUMN_ID,
         GERENTE_EMAIL_LINK_COLUMN_ID, ACTA_PROCUREMENT_COLUMN_ID, ACTA_XLSX_COLUMN_ID]
        + _alias_ids("proyecto", "rubro", "empresa", "no_contrato", "lider_proyecto", "fecha_acta")
    ) if c
]


def _primero(cols, campo):
    return next((cols[c].strip() for c in _alias_ids(campo) if (cols.get(c) or "").strip()), "")


def _dias(desde, ahora):
    if not desde:
        return 0

    return max(0, (ahora.date() - parse_fecha(desde).astimezone(GUATEMALA_TZ).date()).days)


def _alerta(nivel, titulo, causa, que):
    return {"nivel": nivel, "titulo": titulo, "causa": causa, "que": que}


# ------------------------------------------------------------ interpretacion de comentarios
def alerta_desde_motivo(textos, defecto_titulo, defecto_que):
    """Convierte el comentario mas reciente del sistema en una alerta: si
    reconoce el motivo usa su titulo y su 'que hacer'; si no, muestra el texto."""

    for texto in textos:
        n = _norm(texto)

        for palabras, titulo, que in _MOTIVOS:
            if any(_norm(p) in n for p in palabras):
                return _alerta("error", titulo, texto[:400], que)

    causa = textos[0][:400] if textos else "No hay un comentario con el motivo."

    return _alerta("error", defecto_titulo, causa, defecto_que)


def avisos_desde_comentarios(textos):
    """Avisos de generacion (ver avisos.py) que aparecen en el comentario mas
    reciente del sistema, como alertas."""

    for texto in textos:
        if MARCA not in texto:
            continue

        alertas = []

        for titulo in TITULOS:
            i = texto.find(titulo)

            if i < 0:
                continue

            resto = texto[i + len(titulo):]
            detalle, _, que = resto.partition("Qué hacer:")
            que = que.strip().split("\n")[0].strip()
            alertas.append(_alerta("aviso", titulo, detalle.strip(" .\n"), que or "Revise el acta y vuelva a generarla."))

        return alertas

    return []


# ------------------------------------------------------------ estado de una acta
def derivar(it, melissa, ahora, hay_archivo, comentarios=None, comentarios_melissa=None):
    """Estado base de una acta (sin duplicados): paso, nivel, insignia y alertas.

    `it`: item del board principal; `melissa`: su item en el board de Melissa
    (o None); `hay_archivo`: si el documento generado esta guardado."""

    cols = it["columns"]
    estado = (cols.get(ACTA_STATUS_COLUMN_ID) or "").strip()
    gerente = (cols.get(GERENTE_FIRMA_ESTADO_COLUMN_ID) or "").strip()
    proc = (cols.get(ACTA_PROCUREMENT_COLUMN_ID) or "").strip()
    comentarios = comentarios or []
    creado = it.get("created_at")
    dias = _dias(creado, ahora)
    alertas = []
    nivel, insignia, paso, fallo = "curso", "En curso", 1, -1

    if estado == "Rechazado":
        nivel, insignia, paso, fallo = "error", "Rechazada por el sistema", 1, 0
        alertas.append(alerta_desde_motivo(
            comentarios, "El sistema rechazó el acta",
            "Revise el comentario del item, corrija el formulario y vuelva a enviarlo."))
    elif estado == "Error":
        nivel, insignia, paso, fallo = "error", "No se pudo generar", 1, 0
        alertas.append(alerta_desde_motivo(
            comentarios, "No se pudo generar el acta",
            "Use «Volver a generar». Si se repite, avise a soporte."))
    elif estado == "Procesando":
        minutos = (ahora - parse_fecha(it["updated_at"])).total_seconds() / 60 if it.get("updated_at") else 0

        if minutos > MINUTOS_ATASCADA:
            nivel, insignia, paso, fallo = "aviso", "Generación atascada", 1, 0
            alertas.append(_alerta("aviso", "La generación lleva demasiado tiempo",
                                   f"El acta lleva {int(minutos)} minutos en «Procesando».",
                                   "Cambie el estado a «Generar» para intentarlo de nuevo. Si se repite, avise a soporte."))
        else:
            insignia = "Generándose"
    elif estado == "Generado" and not hay_archivo:
        nivel, insignia, paso, fallo = "aviso", "Requiere atención", 1, 0
        alertas.append(_alerta("aviso", "El documento no quedó guardado",
                               "El acta figura como generada, pero el archivo no está en Monday. Sin documento, el Gerente no puede firmar.",
                               "Use «Volver a generar». Si se repite, avise a soporte."))
    elif gerente == "Firmado":
        if proc == ACTA_PROCUREMENT_ESPERA_LABEL:
            lunes = fecha_liberacion(parse_fecha(creado)) if creado else None
            nivel, insignia, paso = "curso", "En espera de horario", 3
            alertas.append(_alerta("curso", "Ingresó fuera de horario",
                                   "Se recibió después del miércoles a las 10:00, así que pasa al siguiente ciclo.",
                                   "Aparecerá en el board de la Arq. Melissa el " +
                                   (lunes.strftime("%d/%m/%Y") + " a las 8:00" if lunes else "próximo lunes") + ". No necesita hacer nada."))
        elif melissa is None:
            nivel, insignia, paso, fallo = "aviso", "Requiere atención", 3, 3
            alertas.append(_alerta("aviso", "No llegó al board de aprobación",
                                   "El Gerente ya firmó, pero el acta no aparece en el board de la Arq. Melissa.",
                                   "Avise a soporte con el nombre del acta para revisarla."))
        else:
            e = (melissa["columns"].get(FIRMA_ESTADO_COLUMN_ID) or "").strip()
            en = _norm(e)

            if en.startswith("firmado"):
                nivel, insignia, paso = "ok", "Completada", 5
            elif "rechaz" in en:
                nivel, insignia, paso, fallo = "error", "Rechazada en aprobación", 4, 3
                textos = comentarios_melissa or []
                alertas.append(_alerta("error", "La Arq. Melissa Alvarenga la rechazó",
                                       ("«" + textos[0][:400] + "»") if textos else "No dejó un comentario con el motivo.",
                                       "Corrija lo indicado y vuelva a enviar el acta desde el formulario."))
            else:
                nivel, insignia, paso = "curso", "En aprobación", 4
    elif gerente == GERENTE_FIRMA_ESTADO_PENDIENTE:
        nivel, insignia, paso = "curso", "Esperando al Gerente", 2

        if dias >= 3:
            fuerte = dias >= 7
            alertas.append(_alerta("aviso" if fuerte else "curso", f"Lleva {dias} días sin firma",
                                   "El Gerente todavía no ha firmado esta acta.",
                                   "Recuérdeselo directamente. El sistema también le envía recordatorios a la semana, a las dos y a las tres."))
    elif estado == "Generado":
        nivel, insignia, paso = "curso", "Lista para enviar al Gerente", 1
        alertas.append(_alerta("curso", "Falta enviarla al Gerente",
                               "El acta ya se generó, pero todavía no se envió a firma.",
                               "Revise el documento y, cuando esté listo, cambie «Enviar a Gerente» a «Enviar»."))
    else:
        nivel, insignia, paso = "curso", "En cola para generarse", 1

    if estado == "Generado" and hay_archivo:
        alertas.extend(avisos_desde_comentarios(comentarios))

    return {"nivel": nivel, "insignia": insignia, "paso": paso, "fallo": fallo, "alertas": alertas, "dias": dias}


def _con_duplicados(actas, todos, ahora):
    """Marca como posible duplicado a la acta mas nueva cuando existe otra, de
    los ultimos DIAS_DUPLICADO dias, con el mismo contratista, rubro y proyecto."""

    def llave(it):
        c = it["columns"]
        return (_norm(_primero(c, "empresa")), _norm(_primero(c, "rubro") or it.get("name")), _norm(_primero(c, "proyecto")))

    indice = {}

    for it in todos:
        if (it["columns"].get(ACTA_STATUS_COLUMN_ID) or "").strip() in ("Rechazado", "Error"):
            continue

        indice.setdefault(llave(it), []).append(it)

    for a in actas:
        it = a["_item"]
        k = llave(it)

        if not k[0] or not k[1] or a["nivel"] in ("ok", "error"):
            continue

        previas = [
            o for o in indice.get(k, [])
            if o["id"] != it["id"] and o.get("created_at") and it.get("created_at")
            and parse_fecha(o["created_at"]) < parse_fecha(it["created_at"])
            and parse_fecha(it["created_at"]) - parse_fecha(o["created_at"]) <= timedelta(days=DIAS_DUPLICADO)
        ]

        if not previas:
            continue

        o = max(previas, key=lambda x: parse_fecha(x["created_at"]))
        cuando = parse_fecha(o["created_at"]).astimezone(GUATEMALA_TZ).strftime("%d/%m/%Y")
        a["alertas"].append(_alerta(
            "aviso", "Se parece a otra acta enviada hace poco",
            f"Mismo contratista, rubro y proyecto que «{_primero(o['columns'], 'rubro') or o.get('name')}» "
            f"(contrato {_primero(o['columns'], 'no_contrato') or 'sin número'}), enviada el {cuando}"
            + (f" por {_primero(o['columns'], 'lider_proyecto')}" if _primero(o["columns"], "lider_proyecto") else "") + ".",
            "Si es un adicional, indíquelo en el nombre del rubro. Si está repetida, cancele una de las dos."))


def _grupo(a):
    if a["nivel"] == "ok":
        return "ok"

    if a["insignia"].startswith("Rechazada") or a["nivel"] == "error":
        return "rechazadas"

    if a["nivel"] == "aviso":
        return "atencion"

    return "curso"


def armar(items, melissa_items, comentarios, comentarios_melissa, ahora, visible):
    """Lista de actas ya derivadas. `items`: todo el board principal;
    `visible(it)`: si la acta es de este usuario; `comentarios[id]` y
    `comentarios_melissa[id]`: textos de comentarios (mas nuevo primero)."""

    por_pa = {}

    for m in melissa_items:
        pa = (m["columns"].get(FIRMA_PA_ITEM_ID_COLUMN_ID) or "").strip()

        if pa:
            por_pa[pa] = m

    actas = []

    for it in items:
        if not visible(it):
            continue

        melissa = por_pa.get(str(it["id"]))
        hay_archivo = bool((it["columns"].get(ACTA_XLSX_COLUMN_ID) or "").strip()) or it.get("_archivo_confirmado", False)
        d = derivar(it, melissa, ahora, hay_archivo, comentarios.get(str(it["id"])),
                    comentarios_melissa.get(str(melissa["id"])) if melissa else None)

        if d["nivel"] == "ok" and d["dias"] > DIAS_VENTANA:
            continue

        c = it["columns"]
        fecha = _primero(c, "fecha_acta")

        if not fecha and it.get("created_at"):
            fecha = parse_fecha(it["created_at"]).astimezone(GUATEMALA_TZ).strftime("%Y-%m-%d")

        d.update({
            "id": str(it["id"]),
            "rubro": _primero(c, "rubro") or it.get("name", ""),
            "proyecto": _primero(c, "proyecto"),
            "empresa": _primero(c, "empresa"),
            "lider": _primero(c, "lider_proyecto"),
            "no_contrato": _primero(c, "no_contrato"),
            "fecha": display_date(fecha) or "—",
            "pendiente_gerente": (c.get(GERENTE_FIRMA_ESTADO_COLUMN_ID) or "").strip() == GERENTE_FIRMA_ESTADO_PENDIENTE,
            "_item": it,
        })
        actas.append(d)

    _con_duplicados(actas, items, ahora)

    for a in actas:
        # La severidad de la acta es la de su peor alerta.
        for al in a["alertas"]:
            if _SEVERIDAD[al["nivel"]] > _SEVERIDAD[a["nivel"]]:
                a["nivel"] = al["nivel"]

                if a["insignia"] == "En curso":
                    a["insignia"] = "Requiere atención"

        a["grupo"] = _grupo(a)
        a.pop("_item", None)

    actas.sort(key=lambda a: (-_SEVERIDAD[a["nivel"]], -a["paso"] if a["nivel"] == "ok" else 0))

    return actas


# ------------------------------------------------------------ llamadas a Monday
_cache_comentarios = {}
_TTL = 120


def _comentarios(item_id, version):
    hit = _cache_comentarios.get((item_id, version))

    if hit and time.time() - hit[0] < _TTL:
        return hit[1]

    try:
        textos = [u["text"] for u in get_item_updates(item_id, 8) if u["text"]]
    except Exception as e:
        print(f"ESTADO_ACTAS: no se pudieron leer los comentarios de {item_id}: {e}", flush=True)
        return []

    _cache_comentarios[(item_id, version)] = (time.time(), textos)

    return textos


def actas_del_usuario(sesion, ahora=None):
    """Las actas que este usuario debe ver: las de su correo si es Gerente y las
    que llevan su nombre como Lider si es Lider."""

    ahora = ahora or datetime.now(timezone.utc)
    correo = (sesion.get("email") or "").strip().lower()
    nombres_lider = {_norm(n) for n in (sesion.get("lider"), sesion.get("name")) if n} if sesion.get("lider") else set()
    es_gerente = bool(sesion.get("gerente"))

    items = list_board_items(ACTA_BOARD_ID, COLUMNAS_ACTA)
    melissa = list_board_items(FIRMA_BOARD_ID, [FIRMA_ESTADO_COLUMN_ID, FIRMA_PA_ITEM_ID_COLUMN_ID])
    del_lider = _clasificador_de_lideres(items)

    def visible(it):
        c = it["columns"]

        if es_gerente and (c.get(GERENTE_EMAIL_LINK_COLUMN_ID) or "").strip().lower() == correo:
            return True

        if sesion.get("lider") and directorio.activo():
            persona = del_lider(it)

            return bool(persona and persona["correo"] == correo)

        return bool(nombres_lider) and _norm(_primero(c, "lider_proyecto")) in nombres_lider

    mias = [it for it in items if visible(it)]
    pa_mios = {str(it["id"]) for it in mias}
    melissa_rechazados = [
        m for m in melissa
        if (m["columns"].get(FIRMA_PA_ITEM_ID_COLUMN_ID) or "").strip() in pa_mios
        and "rechaz" in _norm(m["columns"].get(FIRMA_ESTADO_COLUMN_ID))
    ]

    # Comentarios que hacen falta: motivo de rechazos/errores y avisos de generacion.
    pedir = {}

    for it in mias:
        e = (it["columns"].get(ACTA_STATUS_COLUMN_ID) or "").strip()

        if e in ("Rechazado", "Error", "Generado"):
            pedir[("acta", str(it["id"]))] = it.get("updated_at") or ""

    for m in melissa_rechazados:
        pedir[("melissa", str(m["id"]))] = m.get("updated_at") or ""

    comentarios, comentarios_melissa = {}, {}

    if pedir:
        pool = ThreadPoolExecutor(max_workers=4)
        futuros = {k: pool.submit(_comentarios, k[1], v) for k, v in pedir.items()}
        wait(futuros.values(), timeout=15)
        pool.shutdown(wait=False)

        for (tipo, i), f in futuros.items():
            textos = f.result() if f.done() and not f.exception() else []
            (comentarios if tipo == "acta" else comentarios_melissa)[i] = textos

    # Actas "Generado" sin archivo segun la lista: se confirma con el item completo
    # (la columna de archivos puede venir vacia en el listado aunque si exista).
    for it in mias:
        c = it["columns"]

        if (c.get(ACTA_STATUS_COLUMN_ID) or "").strip() == "Generado" and not (c.get(ACTA_XLSX_COLUMN_ID) or "").strip():
            try:
                from utils.monday_client import get_file_public_url
                it["_archivo_confirmado"] = bool(get_file_public_url(get_item(it["id"]), ACTA_XLSX_COLUMN_ID))
            except Exception:
                it["_archivo_confirmado"] = True  # ante la duda, no alarmar

    return armar(items, melissa, comentarios, comentarios_melissa, ahora, visible)



# ------------------------------------------------------------ a que lider pertenece cada acta
def _clasificador_de_lideres(items):
    """Devuelve una funcion item -> persona del directorio (o None) que dice de
    que Lider es cada acta. Orden de confianza: 1) quien creo el item en Monday, si
    ese dato sirve (una cuenta que crea casi todo es la del formulario, no el
    Lider); 2) el nombre escrito en el formulario, reconocido con tolerancia."""

    if not directorio.activo():
        return lambda it: None

    lideres = [p for p in directorio.personas() if "lider" in p["roles"] and p["acceso"] == "aprobado"]
    por_correo = {p["correo"]: p for p in lideres if p["correo"]}
    conteo = {}

    for it in items:
        e = it.get("creator_email")

        if e:
            conteo[e] = conteo.get(e, 0) + 1

    # Una sola cuenta creando la mayoria de las actas = cuenta generica del formulario.
    genericos = {e for e, n in conteo.items() if len(items) >= 10 and n / len(items) > 0.6}
    memo = {}

    def del_lider(it):
        e = it.get("creator_email")

        if e and e not in genericos and e in por_correo:
            return por_correo[e]

        escrito = _primero(it["columns"], "lider_proyecto")

        if escrito not in memo:
            memo[escrito] = identidad.reconocer(escrito, lideres)

        return memo[escrito][0]

    del_lider.sugerir = lambda it: identidad.reconocer(_primero(it["columns"], "lider_proyecto"), lideres)[1]

    return del_lider


def actas_sin_lider(ahora=None):
    """Actas recientes cuyo Lider no se pudo reconocer: [{id, rubro, proyecto,
    escrito, fecha, sugerencia}], para que un administrador confirme a quien
    pertenecen (queda guardado como alias)."""

    ahora = ahora or datetime.now(timezone.utc)
    items = list_board_items(ACTA_BOARD_ID, COLUMNAS_ACTA)
    del_lider = _clasificador_de_lideres(items)
    sin = []

    for it in items:
        if not it.get("created_at") or _dias(it["created_at"], ahora) > DIAS_VENTANA:
            continue

        if del_lider(it):
            continue

        c = it["columns"]
        sugerida = del_lider.sugerir(it) if hasattr(del_lider, "sugerir") else None
        sin.append({
            "id": str(it["id"]),
            "rubro": _primero(c, "rubro") or it.get("name", ""),
            "proyecto": _primero(c, "proyecto"),
            "escrito": _primero(c, "lider_proyecto"),
            "fecha": display_date(parse_fecha(it["created_at"]).astimezone(GUATEMALA_TZ).strftime("%Y-%m-%d")),
            "sugerencia": {"id": sugerida["id"], "nombre": sugerida["nombre"]} if sugerida else None,
        })

    return sin
