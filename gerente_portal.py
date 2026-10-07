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
from html import escape
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
from firma_gerente_routes import _error_page, _page, _rate_limited
from gerente_link import make_token
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
        "proyecto", "rubro", "empresa", "no_contrato"
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
        })

    return pendientes


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
            return _error_page("Esta funcion todavia no esta disponible."), 404

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
        return _error_page("Esta funcion todavia no esta disponible."), 404

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
        return _error_page("Esta funcion todavia no esta disponible."), 404

    state = request.args.get("state", "")
    code = request.args.get("code", "")

    if not code or not state or state != request.cookies.get(STATE_COOKIE):
        return _error_page("No se pudo verificar el inicio de sesion. Intente de nuevo desde el enlace del correo."), 400

    try:
        nombre, correo = _usuario_de_monday(_codigo_a_token(code))
        correo = (correo or "").strip().lower()
        gerente = _es_gerente(correo)
    except Exception as e:
        print(f"GERENTE_PORTAL: error en el inicio de sesion: {e}", flush=True)
        return _error_page("No se pudo iniciar sesion con Monday. Intente de nuevo."), 502

    if not gerente:
        print(f"GERENTE_PORTAL: acceso denegado, el correo {correo!r} no esta en el board de Gerentes", flush=True)
        return _error_page("Su cuenta de Monday no esta registrada como Gerente de Proyecto."), 403

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
        return _error_page("No se pudieron cargar sus actas. Intente de nuevo."), 500

    return _pagina_pendientes(sesion, actas)


@gerente_portal_bp.get("/gerente/documento/<item_id>")
@_rate_limited
@_requiere_sesion
def documento(sesion, item_id):
    if item_id not in {a["id"] for a in actas_pendientes(sesion["email"])}:
        return _error_page("Esa acta no esta entre sus pendientes."), 403

    url = get_file_public_url(get_item(item_id), ACTA_XLSX_COLUMN_ID)

    if not url:
        return _error_page("El documento no esta disponible todavia."), 404

    return redirect(url)


@gerente_portal_bp.post("/gerente/firmar")
@_rate_limited
@_requiere_sesion
def firmar(sesion):
    if not _mismo_origen():
        return _error_page("Solicitud no valida."), 403

    ids = request.form.getlist("item_ids")
    firma = request.form.get("signature_data_url", "")

    if not request.form.get("confirmar"):
        return _error_page("Debe confirmar que reviso los documentos seleccionados."), 400

    if not ids or not firma.startswith("data:image"):
        return _error_page("Seleccione al menos un acta y dibuje o suba su firma."), 400

    validos = {a["id"]: a for a in actas_pendientes(sesion["email"])}
    ids = [i for i in dict.fromkeys(ids)]

    if any(i not in validos for i in ids):
        return _error_page("Alguna de las actas seleccionadas ya no esta entre sus pendientes. Recargue la pagina."), 409

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
        return _error_page("No se encontro ese proceso."), 404

    return _pagina_trabajo(job_id)


@gerente_portal_bp.get("/gerente/trabajo/<job_id>/estado")
@_requiere_sesion
def trabajo_estado(sesion, job_id):
    job = _jobs.get(job_id)

    if not job or job["email"] != sesion["email"]:
        return jsonify({"error": "no encontrado"}), 404

    return jsonify({"done": job["done"], "items": job["items"]})


# --------------------------------------------------------------------- paginas
_CSS = """
<style>
  .card.wide{max-width:760px}
  table.actas{width:100%;border-collapse:collapse;font-size:.85rem}
  table.actas th{text-align:left;color:#8c8f97;font-weight:600;font-size:.72rem;text-transform:uppercase;padding:6px 8px}
  table.actas td{padding:9px 8px;border-top:1px solid #eee;vertical-align:middle}
  table.actas a{color:var(--accent-dark)}
  .who{font-size:.8rem;color:#5b616c;margin-bottom:14px}
  .estado-ok{color:#1a7f37;font-weight:600}.estado-err{color:#b42318;font-weight:600}
  .vacio{padding:18px;text-align:center;color:#5b616c}
  .confirm{display:flex;gap:8px;align-items:flex-start;font-size:.85rem;margin:14px 0}
  canvas.pad{border:1px dashed #b9b5a8;border-radius:10px;background:#fff;touch-action:none;max-width:100%}
</style>
"""

_PAD_JS = """
<script>
  var c = document.getElementById('pad'), ctx = c.getContext('2d'), drawing = false, dirty = false;
  ctx.lineWidth = 2; ctx.lineCap = 'round'; ctx.strokeStyle = '#20242b';
  function pos(e){var r=c.getBoundingClientRect(),t=e.touches?e.touches[0]:e;
    return {x:(t.clientX-r.left)*(c.width/r.width), y:(t.clientY-r.top)*(c.height/r.height)};}
  function st(e){drawing=true;dirty=true;var p=pos(e);ctx.beginPath();ctx.moveTo(p.x,p.y);e.preventDefault();}
  function mv(e){if(!drawing)return;var p=pos(e);ctx.lineTo(p.x,p.y);ctx.stroke();e.preventDefault();}
  function en(){drawing=false;}
  c.addEventListener('mousedown',st);c.addEventListener('mousemove',mv);window.addEventListener('mouseup',en);
  c.addEventListener('touchstart',st,{passive:false});c.addEventListener('touchmove',mv,{passive:false});c.addEventListener('touchend',en);
  document.getElementById('clear').onclick=function(){ctx.clearRect(0,0,c.width,c.height);dirty=false;document.getElementById('sig').value='';document.getElementById('file').value='';};
  document.getElementById('file').onchange=function(e){var f=e.target.files[0];if(!f)return;var rd=new FileReader();
    rd.onload=function(){document.getElementById('sig').value=rd.result;dirty=false;};rd.readAsDataURL(f);};
  document.getElementById('form').onsubmit=function(e){
    if(dirty){document.getElementById('sig').value=c.toDataURL('image/png');}
    if(!document.querySelector('input[name=item_ids]:checked')){e.preventDefault();alert('Seleccione al menos un acta.');return;}
    if(!document.getElementById('sig').value){e.preventDefault();alert('Dibuje o suba su firma.');return;}
    document.getElementById('go').disabled=true;document.getElementById('go').textContent='Firmando...';};
  document.getElementById('all').onchange=function(e){document.querySelectorAll('input[name=item_ids]').forEach(function(i){i.checked=e.target.checked;});};
</script>
"""


def _pagina_pendientes(sesion, actas):
    if not actas:
        cuerpo = '<div class="vacio">No tiene actas pendientes de firma. Cuando llegue una, aparecera aqui.</div>'
    else:
        filas = "".join(
            f'<tr><td><input type="checkbox" name="item_ids" value="{escape(a["id"])}"></td>'
            f'<td>{escape(a["proyecto"])}</td><td>{escape(a["rubro"])}</td>'
            f'<td>{escape(a["empresa"])}</td><td>{escape(a["no_contrato"])}</td>'
            f'<td><a href="/gerente/documento/{escape(a["id"])}" target="_blank" rel="noopener">Ver documento</a></td></tr>'
            for a in actas
        )
        cuerpo = f"""
        <form id="form" method="post" action="/gerente/firmar">
          <table class="actas">
            <tr><th><input type="checkbox" id="all" title="Seleccionar todas"></th><th>Proyecto</th><th>Rubro</th><th>Empresa</th><th>Contrato</th><th></th></tr>
            {filas}
          </table>
          <div class="section-label" style="margin-top:20px">Firma</div>
          <canvas id="pad" class="pad" width="320" height="200"></canvas>
          <div class="draw-actions"><button type="button" class="link-btn" id="clear">Borrar</button></div>
          <div style="font-size:.8rem;color:#5b616c;margin-top:8px">O suba una imagen de su firma: <input type="file" id="file" accept="image/*"></div>
          <input type="hidden" name="signature_data_url" id="sig">
          <label class="confirm"><input type="checkbox" name="confirmar" value="1" required>
            <span>Revise los documentos seleccionados y apruebo su contenido.</span></label>
          <button type="submit" class="submit-btn" id="go">Firmar las seleccionadas</button>
        </form>{_PAD_JS}"""

    return _page(f"""
    <div class="card wide"><div class="card-accent"></div><div class="card-body">
      <h1>Mis actas pendientes</h1>
      <div class="who">Sesion iniciada como {escape(sesion.get('name') or sesion['email'])} ({escape(sesion['email'])}) -
        <a href="/gerente/salir">Cerrar sesion</a></div>
      {cuerpo}
    </div></div>{_CSS}""")


def _pagina_trabajo(job_id):
    return _page(f"""
    <div class="card wide"><div class="card-accent"></div><div class="card-body">
      <h1>Firmando actas</h1>
      <div class="subtitle">No cierre esta pagina hasta que termine. Cada acta tarda unos segundos.</div>
      <table class="actas" id="lista"></table>
      <p id="fin" hidden><a href="/gerente/pendientes">Volver a mis actas pendientes</a></p>
    </div></div>{_CSS}
    <script>
      function pintar(d){{
        var t = {{pendiente:'En espera', firmando:'Firmando...', firmado:'Firmada', error:'Error'}};
        document.getElementById('lista').innerHTML = d.items.map(function(i){{
          var cls = i.estado === 'firmado' ? 'estado-ok' : (i.estado === 'error' ? 'estado-err' : '');
          var msg = i.mensaje ? ' - ' + i.mensaje.replace(/</g,'&lt;') : '';
          return '<tr><td>' + i.nombre.replace(/</g,'&lt;') + '</td><td class="' + cls + '">' + t[i.estado] + msg + '</td></tr>';
        }}).join('');
        if (d.done) {{ document.getElementById('fin').hidden = false; }}
        return d.done;
      }}
      function ciclo(){{
        fetch('/gerente/trabajo/{job_id}/estado').then(function(r){{return r.json();}}).then(function(d){{
          if (!pintar(d)) setTimeout(ciclo, 2500);
        }}).catch(function(){{ setTimeout(ciclo, 4000); }});
      }}
      ciclo();
    </script>""")
