"""Portal del Gerente: "Mis actas pendientes".

El Gerente inicia sesion con su cuenta de Monday (OAuth). Monday dice quien es
(su correo); si ese correo esta en el board de Gerentes, se le muestran solo las
actas que tiene por firmar y puede firmar varias a la vez con una sola firma.
Nada se muestra sin sesion, y la sesion dura GERENTE_SESION_SEGUNDOS.
"""

import secrets
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime
from urllib.parse import urlencode

import requests
from flask import Blueprint, jsonify, make_response, redirect, request
from itsdangerous import BadSignature, URLSafeTimedSerializer

from config import (
    ACTA_BOARD_ID,
    ACTA_XLSX_COLUMN_ID,
    COLUMN_ALIASES,
    GERENTE_EMAIL_COLUMN_ID,
    GERENTE_EMAIL_LINK_COLUMN_ID,
    GERENTE_FIRMA_ESTADO_COLUMN_ID,
    GERENTE_FIRMA_ESTADO_PENDIENTE,
    GERENTE_LINK_SECRET_KEY,
    GERENTE_PORTAL_BASE_URL,
    GERENTE_SESION_SEGUNDOS,
    GERENTES_BOARD_ID,
    MONDAY_OAUTH_CLIENT_ID,
    MONDAY_OAUTH_CLIENT_SECRET,
)
from firma_gerente import apply_gerente_signature
from firma_gerente_routes import _rate_limited
from gerente_link import make_token
from gerente_portal_ui import pagina_error, pagina_pendientes, pagina_trabajo
from control_facturas import _monto_cotizacion
from semanas import GUATEMALA_TZ, es_solicitud_tardia, parse_fecha
from utils.acta_builder import display_date
from utils.monday_client import get_file_public_url, get_item, list_board_items

gerente_portal_bp = Blueprint("gerente_portal_bp", __name__)

SESION_COOKIE = "gerente_sesion"
STATE_COOKIE = "gerente_state"
AUTH_URL = "https://auth.monday.com/oauth2/authorize"
TOKEN_URL = "https://auth.monday.com/oauth2/token"
API_URL = "https://api.monday.com/v2"

_jobs = {}
_jobs_lock = threading.Lock()


def habilitado():
    return bool(MONDAY_OAUTH_CLIENT_ID and MONDAY_OAUTH_CLIENT_SECRET and GERENTE_LINK_SECRET_KEY)


def _redirect_uri():
    return f"{GERENTE_PORTAL_BASE_URL.rstrip('/')}/gerente/callback"


def _sesiones():
    return URLSafeTimedSerializer(GERENTE_LINK_SECRET_KEY, salt="gerente-sesion-v1")


# --------------------------------------------------------------------- Monday
def _codigo_a_token(code):
    r = requests.post(
        TOKEN_URL,
        json={
            "client_id": MONDAY_OAUTH_CLIENT_ID,
            "client_secret": MONDAY_OAUTH_CLIENT_SECRET,
            "code": code,
            "redirect_uri": _redirect_uri(),
        },
        timeout=20,
    )
    r.raise_for_status()
    token = r.json().get("access_token")

    if not token:
        raise RuntimeError("Monday no devolvio un access_token")

    return token


def _usuario_de_monday(access_token):
    """(nombre, correo) de la cuenta de Monday que acaba de iniciar sesion."""

    for autorizacion in (access_token, f"Bearer {access_token}"):
        r = requests.post(
            API_URL,
            json={"query": "query { me { id name email } }"},
            headers={"Authorization": autorizacion, "Content-Type": "application/json"},
            timeout=20,
        )

        if r.status_code == 401:
            continue

        r.raise_for_status()
        me = (r.json().get("data") or {}).get("me") or {}

        return (me.get("name") or "").strip(), (me.get("email") or "").strip().lower()

    raise RuntimeError("Monday rechazo el token al consultar al usuario")


def _es_gerente(correo):
    """Nombre del Gerente cuyo correo (en el board de Gerentes) es `correo`, o None."""

    correo = (correo or "").strip().lower()

    if not correo:
        return None

    for it in list_board_items(GERENTES_BOARD_ID, [GERENTE_EMAIL_COLUMN_ID]):
        if (it["columns"].get(GERENTE_EMAIL_COLUMN_ID) or "").strip().lower() == correo:
            return it.get("name") or correo

    return None


def _alias_ids(*campos):
    ids = []

    for campo in campos:
        ids.extend(c for c in COLUMN_ALIASES.get(campo, []) if c)

    return ids


def actas_pendientes(correo):
    """Actas del board principal que este Gerente tiene por firmar: su correo
    en "Gerente Correo" y estado "Link Enviado"."""

    correo = (correo or "").strip().lower()
    columnas = [GERENTE_EMAIL_LINK_COLUMN_ID, GERENTE_FIRMA_ESTADO_COLUMN_ID] + _alias_ids(
        "proyecto", "rubro", "empresa", "no_contrato", "lider_proyecto", "fecha_acta"
    )
    pendientes = []

    for it in list_board_items(ACTA_BOARD_ID, columnas):
        cols = it["columns"]

        if (cols.get(GERENTE_EMAIL_LINK_COLUMN_ID) or "").strip().lower() != correo:
            continue

        if (cols.get(GERENTE_FIRMA_ESTADO_COLUMN_ID) or "").strip() != GERENTE_FIRMA_ESTADO_PENDIENTE:
            continue

        def primero(campo):
            return next((cols[c].strip() for c in _alias_ids(campo) if (cols.get(c) or "").strip()), "")

        pendientes.append({
            "id": str(it["id"]),
            "proyecto": primero("proyecto"),
            "rubro": primero("rubro") or it.get("name", ""),
            "empresa": primero("empresa"),
            "no_contrato": primero("no_contrato"),
            "lider": primero("lider_proyecto"),
            "fecha_acta": primero("fecha_acta"),
            "created_at": it.get("created_at"),
        })

    return pendientes


# ------------------------------------------------------------ datos de cada fila
_monto_cache = {}
_MONTO_TTL = 6 * 3600


def monto_con_iva(item_id):
    """Total de la cotizacion con IVA, o None si no se pudo calcular. Leer el
    Excel de cada acta tarda, asi que se recuerda un rato por acta."""

    hit = _monto_cache.get(item_id)

    if hit and time.time() - hit[0] < _MONTO_TTL:
        return hit[1]

    try:
        monto = _monto_cotizacion(get_item(item_id)) or None
    except Exception as e:
        print(f"GERENTE_PORTAL: no se pudo calcular el monto de {item_id}: {e}", flush=True)
        return None

    _monto_cache[item_id] = (time.time(), monto)

    return monto


def _dias_desde(created_at, ahora=None):
    if not created_at:
        return 0

    ahora = ahora or datetime.now(GUATEMALA_TZ)

    return max(0, (ahora.date() - parse_fecha(created_at).astimezone(GUATEMALA_TZ).date()).days)


def enriquecer(actas, ahora=None):
    """Agrega a cada acta lo que muestra la pantalla: fecha, monto con IVA,
    dias de espera y si ingreso fuera de horario. Los montos se calculan en
    paralelo y, si alguno tarda demasiado, se muestra "—" (ya calculado, queda
    en cache para la siguiente carga)."""

    pool = ThreadPoolExecutor(max_workers=4)
    futuros = {a["id"]: pool.submit(monto_con_iva, a["id"]) for a in actas}
    wait(futuros.values(), timeout=12)
    pool.shutdown(wait=False)

    for a in actas:
        fecha = a.get("fecha_acta") or ""
        creado = a.get("created_at")

        if not fecha and creado:
            fecha = parse_fecha(creado).astimezone(GUATEMALA_TZ).strftime("%Y-%m-%d")

        f = futuros[a["id"]]
        monto = f.result() if f.done() and not f.exception() else None

        a["fecha"] = display_date(fecha) or "—"
        a["monto"] = f"Q {monto:,.2f}" if monto else "—"
        a["edad"] = _dias_desde(creado, ahora)
        a["tardia"] = bool(creado) and es_solicitud_tardia(parse_fecha(creado))

    return actas


# --------------------------------------------------------------------- sesion
def _sesion_actual():
    cookie = request.cookies.get(SESION_COOKIE)

    if not cookie or not GERENTE_LINK_SECRET_KEY:
        return None

    try:
        return _sesiones().loads(cookie, max_age=GERENTE_SESION_SEGUNDOS)
    except BadSignature:  # incluye SignatureExpired
        return None


def _poner_cookie(resp, nombre, valor, segundos):
    resp.set_cookie(nombre, valor, max_age=segundos, httponly=True, secure=request.is_secure or request.headers.get("X-Forwarded-Proto") == "https", samesite="Lax")


def _requiere_sesion(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not habilitado():
            return pagina_error("Esta funcion todavia no esta disponible."), 404

        sesion = _sesion_actual()

        if not sesion:
            return redirect("/gerente/entrar")

        return fn(sesion, *args, **kwargs)

    return wrapper


def _mismo_origen():
    origen = request.headers.get("Origin") or ""

    return not origen or origen.split("://", 1)[-1].rstrip("/") == request.host


# --------------------------------------------------------------------- rutas
@gerente_portal_bp.get("/gerente/entrar")
@_rate_limited
def entrar():
    if not habilitado():
        return pagina_error("Esta funcion todavia no esta disponible."), 404

    state = secrets.token_urlsafe(16)
    url = AUTH_URL + "?" + urlencode({
        "client_id": MONDAY_OAUTH_CLIENT_ID,
        "redirect_uri": _redirect_uri(),
        "state": state,
    })
    resp = make_response(redirect(url))
    _poner_cookie(resp, STATE_COOKIE, state, 600)

    return resp


@gerente_portal_bp.get("/gerente/callback")
@_rate_limited
def callback():
    if not habilitado():
        return pagina_error("Esta funcion todavia no esta disponible."), 404

    state = request.args.get("state", "")
    code = request.args.get("code", "")

    if not code or not state or state != request.cookies.get(STATE_COOKIE):
        return pagina_error("No se pudo verificar el inicio de sesion. Intente de nuevo desde el enlace del correo."), 400

    try:
        nombre, correo = _usuario_de_monday(_codigo_a_token(code))
        correo = (correo or "").strip().lower()
        gerente = _es_gerente(correo)
    except Exception as e:
        print(f"GERENTE_PORTAL: error en el inicio de sesion: {e}", flush=True)
        return pagina_error("No se pudo iniciar sesion con Monday. Intente de nuevo."), 502

    if not gerente:
        print(f"GERENTE_PORTAL: acceso denegado, el correo {correo!r} no esta en el board de Gerentes", flush=True)
        return pagina_error("Su cuenta de Monday no esta registrada como Gerente de Proyecto."), 403

    resp = make_response(redirect("/gerente/pendientes"))
    _poner_cookie(resp, SESION_COOKIE, _sesiones().dumps({"email": correo, "name": gerente}), GERENTE_SESION_SEGUNDOS)
    resp.delete_cookie(STATE_COOKIE)
    print(f"GERENTE_PORTAL: sesion iniciada para {correo}", flush=True)

    return resp


@gerente_portal_bp.get("/gerente/salir")
def salir():
    resp = make_response(redirect("/gerente/entrar"))
    resp.delete_cookie(SESION_COOKIE)

    return resp


@gerente_portal_bp.get("/gerente/pendientes")
@_rate_limited
@_requiere_sesion
def pendientes(sesion):
    try:
        actas = actas_pendientes(sesion["email"])
    except Exception as e:
        print(f"GERENTE_PORTAL: error listando pendientes: {e}", flush=True)
        return pagina_error("No se pudieron cargar sus actas. Intente de nuevo."), 500

    return pagina_pendientes(sesion, enriquecer(actas))


@gerente_portal_bp.get("/gerente/documento/<item_id>")
@_rate_limited
@_requiere_sesion
def documento(sesion, item_id):
    if item_id not in {a["id"] for a in actas_pendientes(sesion["email"])}:
        return pagina_error("Esa acta no esta entre sus pendientes."), 403

    url = get_file_public_url(get_item(item_id), ACTA_XLSX_COLUMN_ID)

    if not url:
        return pagina_error("El documento no esta disponible todavia."), 404

    return redirect(url)


@gerente_portal_bp.post("/gerente/firmar")
@_rate_limited
@_requiere_sesion
def firmar(sesion):
    if not _mismo_origen():
        return pagina_error("Solicitud no valida."), 403

    ids = request.form.getlist("item_ids")
    firma = request.form.get("signature_data_url", "")

    if not request.form.get("confirmar"):
        return pagina_error("Debe confirmar que reviso los documentos seleccionados."), 400

    if not ids or not firma.startswith("data:image"):
        return pagina_error("Seleccione al menos un acta y dibuje o suba su firma."), 400

    validos = {a["id"]: a for a in actas_pendientes(sesion["email"])}
    ids = [i for i in dict.fromkeys(ids)]

    if any(i not in validos for i in ids):
        return pagina_error("Alguna de las actas seleccionadas ya no esta entre sus pendientes. Recargue la pagina."), 409

    job_id = uuid.uuid4().hex
    audit = {
        "ip": request.headers.get("X-Forwarded-For", request.remote_addr),
        "user_agent": request.headers.get("User-Agent", ""),
        "gerente": sesion["email"],
    }
    job = {
        "email": sesion["email"],
        "done": False,
        "items": [
            {"id": i, "nombre": (validos[i]["rubro"] or validos[i]["proyecto"] or i), "estado": "pendiente", "mensaje": ""}
            for i in ids
        ],
    }

    with _jobs_lock:
        _jobs[job_id] = job

    threading.Thread(target=_firmar_lote, args=(job, firma, audit), daemon=True).start()

    return redirect(f"/gerente/trabajo/{job_id}")


def _firmar_lote(job, firma, audit):
    """Firma una por una, con el mismo proceso de la firma individual (candado
    incluido). Un error en una no detiene a las demas."""

    for it in job["items"]:
        it["estado"] = "firmando"

        try:
            apply_gerente_signature(make_token(it["id"], ACTA_BOARD_ID), data_url=firma, audit=audit)
            it["estado"] = "firmado"
        except LookupError as e:
            it["estado"], it["mensaje"] = "error", str(e)
        except Exception as e:
            print(f"GERENTE_PORTAL: error firmando item={it['id']}: {e}", flush=True)
            it["estado"], it["mensaje"] = "error", "No se pudo firmar. Intente de nuevo desde su lista de pendientes."

    job["done"] = True


@gerente_portal_bp.get("/gerente/trabajo/<job_id>")
@_requiere_sesion
def trabajo(sesion, job_id):
    job = _jobs.get(job_id)

    if not job or job["email"] != sesion["email"]:
        return pagina_error("No se encontro ese proceso."), 404

    return pagina_trabajo(job_id)


@gerente_portal_bp.get("/gerente/trabajo/<job_id>/estado")
@_requiere_sesion
def trabajo_estado(sesion, job_id):
    job = _jobs.get(job_id)

    if not job or job["email"] != sesion["email"]:
        return jsonify({"error": "no encontrado"}), 404

    return jsonify({"done": job["done"], "items": job["items"]})
