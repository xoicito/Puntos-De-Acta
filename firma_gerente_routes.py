import base64
import time
from collections import defaultdict
from functools import wraps
from pathlib import Path

from flask import Blueprint, redirect, request

from firma_gerente import apply_gerente_signature, get_current_document_url, resolve_signing_context
from gerente_link import InvalidLinkError

firma_gerente_bp = Blueprint("firma_gerente_bp", __name__)

_ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def _logo_data_uri(filename):
    path = _ASSETS_DIR / filename
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


# Inlined once at import time so the signing page never depends on a
# separate static-file route (one less thing to wire up on Render).
_LOGO_E4 = _logo_data_uri("logo_e4.png")
_LOGO_REFORMA = _logo_data_uri("logo_reforma.png")


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


# E4's own brand orange (from the master template) vs. Reforma's navy -
# picked dynamically per document so the signing page always matches the
# actual Punto de Acta the Gerente is about to sign.
_BRAND_E4 = {
    "accent": "#E05900",
    "accent_dark": "#B84700",
    "tint": "#FFF3EA",
    "logo": _LOGO_E4,
    "logo_alt": "Constructora E4",
}
_BRAND_REFORMA = {
    "accent": "#001545",
    "accent_dark": "#000B26",
    "tint": "#EDF1F9",
    "logo": _LOGO_REFORMA,
    "logo_alt": "Reforma",
}

# The signature box has a fixed, predetermined footprint on purpose - it
# must not stretch or shrink when the browser window is resized. Square,
# so it shares the same aspect ratio as the fullscreen pad below and a
# signature drawn there never gets stretched when copied back down.
_CANVAS_W = 320
_CANVAS_H = 320


def _brand(tipo_plantilla):
    return _BRAND_REFORMA if (tipo_plantilla or "").strip().lower() == "reforma" else _BRAND_E4


def _page_style(brand):
    return f"""
<style>
  :root {{
    --accent: {brand['accent']};
    --accent-dark: {brand['accent_dark']};
    --tint: {brand['tint']};
  }}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;
       background:#f0efec;color:#1c1f26;margin:0;padding:32px 16px 48px;}}
  .card{{max-width:520px;margin:0 auto;background:#fff;border:1px solid #e6e3d9;
        border-radius:14px;overflow:hidden;
        box-shadow:0 1px 2px rgba(0,0,0,.04),0 12px 28px -16px rgba(0,0,0,.18);}}
  .card-accent{{height:5px;background:linear-gradient(90deg,var(--accent),var(--accent-dark));}}
  .card-body{{padding:26px 26px 24px;}}
  .brand-row{{display:flex;align-items:center;gap:14px;margin-bottom:18px;}}
  .brand-row img{{height:44px;width:auto;display:block;}}
  .brand-divider{{width:1px;height:32px;background:#e2e0d6;}}
  h1{{font-size:1.2rem;margin:0 0 4px;color:#1c1f26;}}
  .subtitle{{font-size:.82rem;color:#8c8f97;margin-bottom:18px;}}
  .meta{{font-size:.85rem;color:#5b616c;line-height:1.7;margin-bottom:20px;
        background:var(--tint);border-radius:10px;padding:14px 16px;}}
  .meta b{{color:#1c1f26;}}
  .download-btn{{display:flex;align-items:center;justify-content:center;gap:8px;
                 width:100%;padding:12px;border-radius:9px;
                 border:1px solid #d8d4c8;background:#faf9f5;color:#3a3f47;
                 font-size:.9rem;font-weight:600;text-decoration:underline;box-sizing:border-box;}}
  .download-btn:hover{{background:#f2f0e8;}}
  .download-btn svg{{flex-shrink:0;}}
  .card-spaced{{margin-top:16px;}}
  .section-label{{font-size:.78rem;font-weight:700;letter-spacing:.02em;color:#8c8f97;
                  text-transform:uppercase;margin-bottom:10px;}}
  .tabs{{display:flex;gap:8px;margin-bottom:14px;}}
  .tab-btn{{flex:1;padding:9px;border:1px solid #d8d4c8;background:#faf9f5;border-radius:8px;
           font-size:.88rem;cursor:pointer;color:#4a4f58;}}
  .tab-btn.active{{background:var(--accent);color:#fff;border-color:var(--accent);}}
  .canvas-wrap{{position:relative;display:flex;justify-content:center;}}
  #sig-canvas{{width:{_CANVAS_W}px;max-width:100%;height:auto;aspect-ratio:1/1;
              border:1px solid #d8d4c8;border-radius:8px;touch-action:none;
              background:#fff;display:block;}}
  .expand-btn{{position:absolute;top:8px;right:8px;width:30px;height:30px;
              display:flex;align-items:center;justify-content:center;
              border:1px solid #d8d4c8;border-radius:7px;background:rgba(255,255,255,.9);
              color:#4a4f58;cursor:pointer;padding:0;}}
  .expand-btn:hover{{background:#fff;color:var(--accent-dark);}}
  .draw-actions{{display:flex;justify-content:flex-end;margin-top:6px;}}
  .link-btn{{background:none;border:none;color:var(--accent-dark);font-size:.82rem;cursor:pointer;padding:4px;}}
  #upload-pane input{{width:100%;padding:10px;border:1px solid #d8d4c8;border-radius:8px;
                      background:#faf9f5;box-sizing:border-box;}}
  .submit-btn{{width:100%;margin-top:18px;padding:13px;border:none;border-radius:9px;
              background:var(--accent);color:#fff;font-size:1rem;font-weight:600;cursor:pointer;}}
  .submit-btn:hover{{background:var(--accent-dark);}}
  .submit-btn:disabled{{opacity:.5;cursor:not-allowed;}}
  .note{{font-size:.78rem;color:#8c8f97;margin-top:10px;line-height:1.5;}}
  .error-card .card-body h1{{color:#a8651c;}}
  .success-card .card-body h1{{color:#3a7d44;}}
  [hidden]{{display:none!important;}}
  .fs-overlay{{position:fixed;inset:0;background:#fff;z-index:1000;
              display:flex;flex-direction:column;padding:16px;box-sizing:border-box;}}
  .fs-header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;}}
  .fs-header span{{font-size:.95rem;font-weight:600;color:#1c1f26;}}
  .fs-close{{border:1px solid #d8d4c8;background:#faf9f5;border-radius:7px;padding:7px 12px;
            font-size:.85rem;color:#4a4f58;cursor:pointer;}}
  .fs-canvas-wrap{{flex:1;display:flex;align-items:center;justify-content:center;
                  min-height:0;overflow:hidden;}}
  #fs-canvas{{border:1px solid #d8d4c8;border-radius:8px;
             touch-action:none;background:#fff;display:block;}}
  .fs-actions{{display:flex;gap:10px;margin-top:12px;}}
  .fs-actions .link-btn{{flex-shrink:0;}}
  .fs-actions .submit-btn{{margin-top:0;}}
</style>
"""


def _logo_header():
    return f"""
      <div class="brand-row">
        <img src="{_LOGO_E4}" alt="Constructora E4">
        <div class="brand-divider"></div>
        <img src="{_LOGO_REFORMA}" alt="Reforma">
      </div>
    """


def _page(body, tipo_plantilla=""):
    brand = _brand(tipo_plantilla)
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Firma - Punto de Acta</title>
{_page_style(brand)}
</head><body>{body}</body></html>"""


def _error_page(message):
    return _page(f"""
    <div class="card error-card">
      <div class="card-accent"></div>
      <div class="card-body">
        <h1>No se puede continuar</h1>
        <p>{message}</p>
      </div>
    </div>
    """)


def _success_page(tipo_plantilla=""):
    return _page(f"""
    <div class="card success-card">
      <div class="card-accent"></div>
      <div class="card-body">
        <h1>Firmado correctamente</h1>
        <p>El documento fue firmado y actualizado en Monday. Ya puede cerrar esta pagina.</p>
      </div>
    </div>
    """, tipo_plantilla)


def _form_page(ctx):
    brand = _brand(ctx.get("tipo_plantilla"))
    return _page(f"""
    <div class="card">
      <div class="card-accent"></div>
      <div class="card-body">
        {_logo_header()}
        <h1>Firmar Punto de Acta</h1>
        <div class="subtitle">Revise los datos y firme para continuar el proceso de aprobacion.</div>
        <div class="meta">
          <div><b>Proyecto:</b> {ctx['proyecto']}</div>
          <div><b>Contrato:</b> {ctx['no_contrato']}</div>
          <div><b>Empresa:</b> {ctx['empresa']}</div>
        </div>

        <a class="download-btn" href="/firmar-gerente/{ctx['item_id_token']}/descargar" target="_blank" rel="noopener">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 15V3"/><path d="M8 11l4 4 4-4"/><path d="M21 21H3"/></svg>
          Descargar Punto de Acta (como lo envio el Lider)
        </a>
      </div>
    </div>

    <div class="card card-spaced">
      <div class="card-accent"></div>
      <div class="card-body">
        <div class="section-label">Firma</div>
        <div class="tabs">
          <button type="button" class="tab-btn active" id="tab-draw">Dibujar firma</button>
          <button type="button" class="tab-btn" id="tab-upload">Subir imagen</button>
        </div>

        <form id="firma-form" method="post" enctype="multipart/form-data">
          <div id="draw-pane">
            <div class="canvas-wrap">
              <canvas id="sig-canvas" width="{_CANVAS_W}" height="{_CANVAS_H}"></canvas>
              <button type="button" class="expand-btn" id="expand-btn" title="Agrandar para firmar">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M21 8V5a2 2 0 0 0-2-2h-3"/><path d="M3 16v3a2 2 0 0 0 2 2h3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/></svg>
              </button>
            </div>
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
    </div>

    <div class="fs-overlay" id="fs-overlay" hidden>
      <div class="fs-header">
        <span>Dibuje su firma</span>
        <button type="button" class="fs-close" id="fs-close">Cerrar</button>
      </div>
      <div class="fs-canvas-wrap"><canvas id="fs-canvas"></canvas></div>
      <div class="fs-actions">
        <button type="button" class="link-btn" id="fs-clear-btn">Borrar</button>
        <button type="button" class="submit-btn" id="fs-use-btn">Usar esta firma</button>
      </div>
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

      // Attaches drawing handlers to a canvas at a given CSS pixel size
      // (device-pixel-ratio scaled internally so strokes stay crisp) and
      // returns a small handle to read/clear/reset it. The small canvas
      // uses a fixed, predetermined size on purpose - it must not grow or
      // shrink when the window is resized. The fullscreen one is sized to
      // the viewport instead, since its whole point is to be roomier.
      function makePad(canvas, cssW, cssH) {{
        var ctx = canvas.getContext('2d');
        var dpr = window.devicePixelRatio || 1;
        canvas.width = cssW * dpr;
        canvas.height = cssH * dpr;
        canvas.style.width = cssW + 'px';
        canvas.style.height = cssH + 'px';
        ctx.scale(dpr, dpr);
        ctx.lineWidth = 2; ctx.lineCap = 'round'; ctx.strokeStyle = '#20242b';

        var drawing = false, hasDrawn = false;

        function pos(e) {{
          var rect = canvas.getBoundingClientRect();
          var t = e.touches ? e.touches[0] : e;
          return {{x: (t.clientX - rect.left) * (cssW / rect.width), y: (t.clientY - rect.top) * (cssH / rect.height)}};
        }}
        function start(e) {{ drawing = true; hasDrawn = true; var p = pos(e); ctx.beginPath(); ctx.moveTo(p.x, p.y); e.preventDefault(); }}
        function move(e) {{ if (!drawing) return; var p = pos(e); ctx.lineTo(p.x, p.y); ctx.stroke(); e.preventDefault(); }}
        function end() {{ drawing = false; }}

        canvas.addEventListener('mousedown', start);
        canvas.addEventListener('mousemove', move);
        window.addEventListener('mouseup', end);
        canvas.addEventListener('touchstart', start, {{passive: false}});
        canvas.addEventListener('touchmove', move, {{passive: false}});
        canvas.addEventListener('touchend', end);

        return {{
          el: canvas,
          ctx: ctx,
          cssW: cssW,
          cssH: cssH,
          clear: function() {{ ctx.clearRect(0, 0, cssW, cssH); hasDrawn = false; }},
          hasDrawn: function() {{ return hasDrawn; }},
          setDrawn: function(v) {{ hasDrawn = v; }}
        }};
      }}

      var CANVAS_W = {_CANVAS_W};
      var CANVAS_H = {_CANVAS_H};
      var mainPad = makePad(document.getElementById('sig-canvas'), CANVAS_W, CANVAS_H);
      // Let the CSS aspect-ratio (not this inline height) govern the
      // visible box, so it can shrink to fit a narrow phone screen
      // without losing its square shape.
      mainPad.el.style.height = 'auto';

      document.getElementById('clear-btn').onclick = function() {{ mainPad.clear(); }};

      // Fullscreen signing: opens an overlay with a much bigger canvas so
      // it's easier to sign on a phone; whatever's drawn there is copied
      // back onto the small canvas (which is what actually gets submitted)
      // when the Gerente taps "Usar esta firma".
      var fsOverlay = document.getElementById('fs-overlay');
      var fsPad = null;

      document.getElementById('expand-btn').onclick = function() {{
        fsOverlay.hidden = false;
        // Square, same as the small canvas, so nothing gets stretched
        // when the drawing is copied back down on "Usar esta firma".
        var side = Math.min(window.innerWidth - 32, window.innerHeight - 140, 700);
        fsPad = makePad(document.getElementById('fs-canvas'), side, side);
        if (mainPad.hasDrawn()) {{
          fsPad.ctx.drawImage(mainPad.el, 0, 0, mainPad.el.width, mainPad.el.height, 0, 0, side, side);
          fsPad.setDrawn(true);
        }}
      }};

      document.getElementById('fs-close').onclick = function() {{ fsOverlay.hidden = true; }};
      document.getElementById('fs-clear-btn').onclick = function() {{ fsPad.clear(); }};

      document.getElementById('fs-use-btn').onclick = function() {{
        if (fsPad.hasDrawn()) {{
          mainPad.ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);
          mainPad.ctx.drawImage(fsPad.el, 0, 0, fsPad.el.width, fsPad.el.height, 0, 0, CANVAS_W, CANVAS_H);
          mainPad.setDrawn(true);
        }}
        fsOverlay.hidden = true;
      }};

      document.getElementById('firma-form').onsubmit = function(e) {{
        if (mode === 'draw') {{
          if (!mainPad.hasDrawn()) {{ e.preventDefault(); alert('Dibuje su firma antes de continuar.'); return; }}
          document.getElementById('signature_data_url').value = mainPad.el.toDataURL('image/png');
        }} else {{
          var f = document.getElementById('signature_file');
          if (!f.files || !f.files.length) {{ e.preventDefault(); alert('Seleccione una imagen antes de continuar.'); return; }}
        }}
        document.getElementById('submit-btn').disabled = true;
        document.getElementById('submit-btn').textContent = 'Firmando...';
      }};
    </script>
    """, ctx.get("tipo_plantilla"))


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

    ctx["item_id_token"] = token

    return _form_page(ctx)


@firma_gerente_bp.get("/firmar-gerente/<token>/descargar")
@_rate_limited
def firmar_gerente_descargar(token):
    try:
        url = get_current_document_url(token)
    except InvalidLinkError as e:
        return _error_page(str(e)), 400
    except Exception as e:
        print(f"GERENTE_FIRMA: error al preparar descarga: {e}")
        return _error_page("Ocurrio un error al preparar la descarga."), 500

    if not url:
        return _error_page("El documento no esta disponible todavia."), 404

    return redirect(url)


@firma_gerente_bp.post("/firmar-gerente/<token>")
@_rate_limited
def firmar_gerente_submit(token):
    audit = {
        "ip": request.headers.get("X-Forwarded-For", request.remote_addr),
        "user_agent": request.headers.get("User-Agent", ""),
    }

    try:
        result = apply_gerente_signature(
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

    return _success_page(result.get("tipo_plantilla"))
