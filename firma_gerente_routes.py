import time
from collections import defaultdict
from functools import wraps

from flask import Blueprint, request

from firma_gerente import apply_gerente_signature, resolve_signing_context
from gerente_link import InvalidLinkError

firma_gerente_bp = Blueprint("firma_gerente_bp", __name__)


# The signing token itself can't realistically be brute-forced (it's a
# cryptographically signed value), but this still limits how fast any one
# IP can hammer the endpoint - basic defense-in-depth against scripted
# probing or accidental retry loops. In-memory, so it resets per worker
# process and isn't shared across multiple gunicorn workers - good enough
# for this app's traffic, not a substitute for a real shared rate limiter
# if this ever needs to scale beyond a single small deployment.
_RATE_LIMIT_WINDOW_SECONDS = 60
_RATE_LIMIT_MAX_REQUESTS = 20
_request_log = defaultdict(list)


def _rate_limited(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        ip = request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"
        now = time.time()

        recent = [t for t in _request_log[ip] if now - t < _RATE_LIMIT_WINDOW_SECONDS]
        recent.append(now)
        _request_log[ip] = recent

        if len(recent) > _RATE_LIMIT_MAX_REQUESTS:
            return _error_page("Demasiados intentos. Espere un momento e intente de nuevo."), 429

        return fn(*args, **kwargs)

    return wrapper


PAGE_STYLE = """
<style>
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
       background:#f4f3f0;color:#20242b;margin:0;padding:24px 16px 48px;}
  .card{max-width:520px;margin:0 auto;background:#fff;border:1px solid #e3e0d6;
        border-radius:12px;padding:24px 22px;box-shadow:0 1px 2px rgba(0,0,0,.04),0 8px 24px -14px rgba(0,0,0,.15);}
  h1{font-size:1.25rem;margin:0 0 6px}
  .meta{font-size:.85rem;color:#6a7280;line-height:1.6;margin-bottom:18px;
        border-bottom:1px solid #eee;padding-bottom:16px}
  .meta b{color:#20242b}
  .tabs{display:flex;gap:8px;margin-bottom:14px}
  .tab-btn{flex:1;padding:9px;border:1px solid #d8d4c8;background:#faf9f5;border-radius:8px;
           font-size:.88rem;cursor:pointer;color:#4a4f58}
  .tab-btn.active{background:#2f5d8a;color:#fff;border-color:#2f5d8a}
  #draw-pane canvas{width:100%;height:180px;border:1px solid #d8d4c8;border-radius:8px;
                     touch-action:none;background:#fff;display:block}
  .draw-actions{display:flex;justify-content:flex-end;margin-top:6px}
  .link-btn{background:none;border:none;color:#2f5d8a;font-size:.82rem;cursor:pointer;padding:4px}
  #upload-pane input{width:100%;padding:10px;border:1px solid #d8d4c8;border-radius:8px;background:#faf9f5}
  .submit-btn{width:100%;margin-top:18px;padding:13px;border:none;border-radius:8px;
              background:#2f5d8a;color:#fff;font-size:1rem;font-weight:600;cursor:pointer}
  .submit-btn:disabled{opacity:.5;cursor:not-allowed}
  .note{font-size:.78rem;color:#8c8f97;margin-top:10px;line-height:1.5}
  .error-card{border-color:#e0b98f}
  .error-card h1{color:#a8651c}
  .success-card h1{color:#3a7d44}
  [hidden]{display:none!important}
</style>
"""


def _page(body):
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Firma - Punto de Acta</title>
{PAGE_STYLE}
</head><body>{body}</body></html>"""


def _error_page(message):
    return _page(f"""
    <div class="card error-card">
      <h1>No se puede continuar</h1>
      <p>{message}</p>
    </div>
    """)


def _success_page():
    return _page("""
    <div class="card success-card">
      <h1>Firmado correctamente</h1>
      <p>El documento fue firmado y actualizado en Monday. Ya puede cerrar esta pagina.</p>
    </div>
    """)


def _form_page(ctx):
    return _page(f"""
    <div class="card">
      <h1>Firmar Punto de Acta</h1>
      <div class="meta">
        <div><b>Proyecto:</b> {ctx['proyecto']}</div>
        <div><b>Contrato:</b> {ctx['no_contrato']}</div>
        <div><b>Empresa:</b> {ctx['empresa']}</div>
      </div>

      <div class="tabs">
        <button type="button" class="tab-btn active" id="tab-draw">Dibujar firma</button>
        <button type="button" class="tab-btn" id="tab-upload">Subir imagen</button>
      </div>

      <form id="firma-form" method="post" enctype="multipart/form-data">
        <div id="draw-pane">
          <canvas id="sig-canvas"></canvas>
          <div class="draw-actions"><button type="button" class="link-btn" id="clear-btn">Borrar</button></div>
          <input type="hidden" name="signature_data_url" id="signature_data_url">
        </div>
        <div id="upload-pane" hidden>
          <input type="file" name="signature_file" id="signature_file" accept="image/*">
        </div>

        <button type="submit" class="submit-btn" id="submit-btn">Firmar documento</button>
        <div class="note">Este enlace es unico y de un solo uso. Al firmar, se inserta su firma en el documento y no podra volver a usarse.</div>
      </form>
    </div>

    <script>
      var tabDraw = document.getElementById('tab-draw');
      var tabUpload = document.getElementById('tab-upload');
      var drawPane = document.getElementById('draw-pane');
      var uploadPane = document.getElementById('upload-pane');
      var mode = 'draw';

      tabDraw.onclick = function() {{
        mode = 'draw'; tabDraw.className = 'tab-btn active'; tabUpload.className = 'tab-btn';
        drawPane.hidden = false; uploadPane.hidden = true;
      }};
      tabUpload.onclick = function() {{
        mode = 'upload'; tabUpload.className = 'tab-btn active'; tabDraw.className = 'tab-btn';
        uploadPane.hidden = false; drawPane.hidden = true;
      }};

      var canvas = document.getElementById('sig-canvas');
      var ctx = canvas.getContext('2d');
      function sizeCanvas() {{
        var rect = canvas.getBoundingClientRect();
        canvas.width = rect.width * 2; canvas.height = rect.height * 2;
        ctx.scale(2, 2); ctx.lineWidth = 2; ctx.lineCap = 'round'; ctx.strokeStyle = '#20242b';
      }}
      sizeCanvas();
      var drawing = false, hasDrawn = false;

      function pos(e) {{
        var rect = canvas.getBoundingClientRect();
        var t = e.touches ? e.touches[0] : e;
        return {{x: t.clientX - rect.left, y: t.clientY - rect.top}};
      }}
      function start(e) {{ drawing = true; hasDrawn = true; var p = pos(e); ctx.beginPath(); ctx.moveTo(p.x, p.y); e.preventDefault(); }}
      function move(e) {{ if (!drawing) return; var p = pos(e); ctx.lineTo(p.x, p.y); ctx.stroke(); e.preventDefault(); }}
      function end() {{ drawing = false; }}

      canvas.addEventListener('mousedown', start);
      canvas.addEventListener('mousemove', move);
      window.addEventListener('mouseup', end);
      canvas.addEventListener('touchstart', start);
      canvas.addEventListener('touchmove', move);
      canvas.addEventListener('touchend', end);

      document.getElementById('clear-btn').onclick = function() {{
        ctx.clearRect(0, 0, canvas.width, canvas.height); hasDrawn = false;
      }};

      document.getElementById('firma-form').onsubmit = function(e) {{
        if (mode === 'draw') {{
          if (!hasDrawn) {{ e.preventDefault(); alert('Dibuje su firma antes de continuar.'); return; }}
          document.getElementById('signature_data_url').value = canvas.toDataURL('image/png');
        }} else {{
          var f = document.getElementById('signature_file');
          if (!f.files || !f.files.length) {{ e.preventDefault(); alert('Seleccione una imagen antes de continuar.'); return; }}
        }}
        document.getElementById('submit-btn').disabled = true;
        document.getElementById('submit-btn').textContent = 'Firmando...';
      }};
    </script>
    """)


@firma_gerente_bp.get("/firmar-gerente/<token>")
@_rate_limited
def firmar_gerente_form(token):
    try:
        ctx = resolve_signing_context(token)
    except InvalidLinkError as e:
        return _error_page(str(e)), 400
    except LookupError as e:
        return _error_page(str(e)), 409
    except Exception as e:
        print(f"GERENTE_FIRMA: error mostrando formulario: {e}")
        return _error_page("Ocurrio un error al cargar el documento."), 500

    return _form_page(ctx)


@firma_gerente_bp.post("/firmar-gerente/<token>")
@_rate_limited
def firmar_gerente_submit(token):
    audit = {
        "ip": request.headers.get("X-Forwarded-For", request.remote_addr),
        "user_agent": request.headers.get("User-Agent", ""),
    }

    try:
        apply_gerente_signature(
            token,
            file_storage=request.files.get("signature_file"),
            data_url=request.form.get("signature_data_url"),
            audit=audit,
        )
    except InvalidLinkError as e:
        return _error_page(str(e)), 400
    except LookupError as e:
        return _error_page(str(e)), 409
    except Exception as e:
        print(f"GERENTE_FIRMA: error al firmar: {e}")
        return _error_page("Ocurrio un error al procesar la firma. Intente de nuevo."), 500

    return _success_page()
