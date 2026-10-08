"""Paginas del portal del Gerente (tema oscuro, IBM Plex Sans).

Solo arma HTML; la logica (sesion, listado, firma) esta en gerente_portal.py.
"""

from html import escape

from firma_gerente_routes import _LOGO_E4, _LOGO_REFORMA

_HEAD = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>__TITULO__</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root{
    color-scheme:dark;
    --concreto:#141B23; --papel:#1C2530; --tinta:#E8ECF0; --tinta-2:#9CA9B6; --regla:#33414F; --regla-2:#2A3541;
    --e4:#D95500; --e4-oscuro:#F26B12; --plano:#86B6E8;
    --reciente:#566475; --atencion:#E0A800; --urgente:#FF6E61;
    --texto:'IBM Plex Sans','Segoe UI',Arial,sans-serif;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--concreto);color:var(--tinta);font:15px/1.5 var(--texto);font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}
  a{color:var(--plano)} button{font:inherit;cursor:pointer}
  :focus-visible{outline:3px solid var(--plano);outline-offset:2px}
  .barra{background:var(--papel);border-bottom:1px solid var(--regla)}
  .barra-in{max-width:1040px;margin:0 auto;padding:12px 20px;display:flex;align-items:center;gap:16px}
  .logos{display:flex;align-items:center;gap:12px;background:#fff;border-radius:8px;padding:6px 12px}
  .logos img{height:30px;display:block}.logos i{width:1px;height:24px;background:#C7CDD3}
  .quien{margin-left:auto;text-align:right;font-size:13px;color:var(--tinta-2);line-height:1.35}
  .quien b{display:block;color:var(--tinta);font-weight:600}
  main{max-width:1040px;margin:0 auto;padding:30px 20px 140px}
  h1{font:600 34px/1.15 var(--texto);letter-spacing:-.015em;margin:0 0 8px}
  .resumen{margin:0 0 22px;color:var(--tinta-2);max-width:60ch;font-size:16px}
  .filtros{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:14px}
  .buscar{flex:1 1 220px;max-width:340px;padding:9px 12px;border:1px solid var(--regla);background:var(--papel);color:var(--tinta);border-radius:6px;font:inherit}
  .buscar::placeholder{color:var(--tinta-2)}
  .chip{padding:7px 12px;border:1px solid var(--regla);background:var(--papel);border-radius:999px;font-size:13px;color:var(--tinta-2)}
  .chip[aria-pressed=true]{background:var(--tinta);border-color:var(--tinta);color:#141B23;font-weight:500}
  .todas{margin-left:auto;font-size:13px;color:var(--tinta-2);display:flex;gap:8px;align-items:center}
  .lamina{position:relative;display:grid;grid-template-columns:44px 1fr auto;gap:0 14px;background:var(--papel);
          border:1px solid var(--regla);border-left:6px solid var(--reciente);border-radius:6px;padding:16px 18px 14px 14px;margin-bottom:12px;
          cursor:pointer;transition:border-color .15s, background .15s, box-shadow .15s}
  .lamina[hidden]{display:none}
  .lamina:hover{border-top-color:var(--tinta-2);border-right-color:var(--tinta-2);border-bottom-color:var(--tinta-2)}
  .lamina[data-edad="2"]{border-left-color:var(--atencion)}
  .lamina[data-edad="4"]{border-left-color:var(--urgente)}
  .lamina.sel{background:#242F3C;border-top-color:var(--e4);border-right-color:var(--e4);border-bottom-color:var(--e4);box-shadow:inset 0 0 0 1px var(--e4)}
  .marca{display:flex;justify-content:center;padding-top:4px}
  .marca input{width:24px;height:24px;accent-color:var(--e4);cursor:pointer}
  .rubro{font:600 19px/1.3 var(--texto);letter-spacing:-.005em;margin:0 0 3px}
  .quien-contrata{color:var(--tinta-2);font-size:14px;margin:0 0 12px}
  .datos{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px 20px;margin:0}
  .datos div{border-top:1px solid var(--regla-2);padding-top:5px}
  .datos dt{font-size:12px;color:var(--tinta-2)} .datos dd{margin:0;font-weight:500}
  .lado{display:flex;flex-direction:column;align-items:flex-end;gap:8px;min-width:150px}
  .edad{font-size:13px;font-weight:600}
  .edad[data-n="2"]{color:var(--atencion)}.edad[data-n="4"]{color:var(--urgente)}.edad[data-n="0"]{color:var(--tinta-2);font-weight:500}
  .btn-sec{padding:9px 16px;border:1px solid var(--e4);background:var(--e4);border-radius:6px;color:#fff;font-size:14px;font-weight:600;text-decoration:none;display:inline-block}
  .btn-sec:hover{background:var(--e4-oscuro);border-color:var(--e4-oscuro)}
  .tardia{font-size:12px;background:#3B3012;color:#F2C94C;padding:2px 8px;border-radius:4px;font-weight:500}
  .vacio{padding:34px 8px;color:var(--tinta-2);font-size:16px}
  .accion{position:fixed;left:0;right:0;bottom:0;background:#0F151B;border-top:1px solid var(--regla);color:#fff;z-index:20}
  .accion-in{max-width:1040px;margin:0 auto;padding:14px 20px;display:flex;align-items:center;gap:16px}
  .accion p{margin:0;font-size:15px}
  .accion .ayuda{display:block;color:var(--tinta-2);font-size:13px}
  .accion.vacia p{color:var(--tinta-2)}
  .btn-firmar{margin-left:auto;background:var(--e4);color:#fff;border:0;border-radius:6px;padding:12px 22px;font-weight:600;font-size:16px}
  .btn-firmar:hover:not(:disabled){background:var(--e4-oscuro)}
  .btn-firmar:disabled{background:#2A3541;color:#7F8C99;cursor:not-allowed}
  .velo{position:fixed;inset:0;background:rgba(5,8,11,.72);opacity:0;pointer-events:none;transition:opacity .2s;z-index:30}
  .velo.abierto{opacity:1;pointer-events:auto}
  .hoja{position:fixed;left:50%;bottom:0;width:min(560px,100%);background:var(--papel);border:1px solid var(--regla);border-bottom:0;border-radius:10px 10px 0 0;padding:22px 22px 24px;
        transform:translate(-50%,105%);transition:transform .25s ease;z-index:31;max-height:94vh;overflow:auto}
  .hoja.abierta{transform:translate(-50%,0)}
  .hoja h2{font:600 24px/1.2 var(--texto);letter-spacing:-.01em;margin:0 0 4px}
  .hoja .sub{margin:0 0 14px;color:var(--tinta-2);font-size:14px}
  .caja-firma{border:2px solid #E8ECF0;border-radius:3px;position:relative;background:#FBFBF9;color:#1B2733}
  .caja-firma canvas{display:block;width:100%;height:190px;touch-action:none}
  .caja-firma .linea{position:absolute;left:18px;right:18px;bottom:44px;border-top:1px solid #6B7682;pointer-events:none}
  .caja-firma .pie{border-top:2px solid #1B2733;padding:7px 12px;font:600 13px var(--texto);display:flex;justify-content:space-between;align-items:center;gap:12px}
  .caja-firma .pie button,.caja-firma .pie label{background:none;border:0;color:#2D5B87;font:14px var(--texto);text-decoration:underline;cursor:pointer}
  .confirma{display:flex;gap:10px;margin:16px 0;font-size:14px;align-items:flex-start}
  .confirma input{width:20px;height:20px;margin-top:2px;accent-color:var(--e4)}
  .hoja .btn-firmar{width:100%;margin:0}
  .cerrar{position:absolute;right:14px;top:12px;background:none;border:0;font-size:26px;line-height:1;color:var(--tinta-2)}
  .tarjeta{max-width:620px;margin:60px auto;padding:0 20px}
  .tarjeta .caja{background:var(--papel);border:1px solid var(--regla);border-radius:8px;padding:26px}
  .tarjeta h1{font-size:26px}
  .proceso{list-style:none;margin:14px 0 0;padding:0}
  .proceso li{display:flex;justify-content:space-between;gap:12px;padding:10px 0;border-top:1px solid var(--regla-2)}
  .ok{color:#5BD07A;font-weight:600}.err{color:var(--urgente);font-weight:600}.trabajando{color:var(--tinta-2)}
  @media (max-width:720px){
    h1{font-size:28px}
    .lamina{grid-template-columns:34px 1fr;padding:14px 14px 12px 10px}
    .lado{grid-column:1 / -1;flex-direction:row;align-items:center;justify-content:space-between;margin-top:12px}
    .todas{margin-left:0;width:100%}.quien{display:none}
  }
  @media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style></head><body>
"""

_BARRA = """<header class="barra"><div class="barra-in">
  <div class="logos"><img src="__E4__" alt="Constructora E4"><i></i><img src="__REF__" alt="Reforma"></div>
  __QUIEN__
</div></header>"""


def _documento(titulo, cuerpo):
    return (_HEAD.replace("__TITULO__", escape(titulo)) + cuerpo + "</body></html>")


def _barra(sesion=None):
    quien = ""

    if sesion:
        quien = (
            f'<div class="quien"><b>{escape(sesion.get("name") or sesion["email"])}</b>'
            f'<a href="/gerente/salir">Cerrar sesión</a></div>'
        )

    return _BARRA.replace("__E4__", _LOGO_E4).replace("__REF__", _LOGO_REFORMA).replace("__QUIEN__", quien)


def pagina_error(mensaje):
    return _documento("Firmas de Punto de Acta", _barra() + f"""
    <div class="tarjeta"><div class="caja"><h1>No se puede continuar</h1>
    <p style="color:var(--tinta-2);margin:0">{escape(mensaje)}</p>
    <p style="margin:18px 0 0"><a href="/gerente/pendientes">Ir a mis actas pendientes</a></p></div></div>""")


def _texto_edad(n):
    if n <= 0:
        return "Llegó hoy"

    return "Lleva 1 día" if n == 1 else f"Lleva {n} días"


def _clase_edad(n):
    return "4" if n >= 4 else ("2" if n >= 2 else "0")


def _resumen(actas):
    if not actas:
        return "No tiene actas pendientes. Cuando llegue una, aparecerá aquí."

    mas_antigua = max(actas, key=lambda a: a["edad"])
    n = len(actas)

    if n == 1:
        return f"Tiene 1 acta pendiente. {_texto_edad(mas_antigua['edad'])} esperando: {mas_antigua['rubro']}." if mas_antigua["edad"] > 0 else "Tiene 1 acta pendiente, llegó hoy."

    if mas_antigua["edad"] <= 0:
        return f"Tiene {n} actas pendientes. Todas llegaron hoy."

    return (f"Tiene {n} actas pendientes. La que más lleva esperando es de hace "
            f"{mas_antigua['edad']} {'día' if mas_antigua['edad'] == 1 else 'días'}: {mas_antigua['rubro']}.")


def _lamina(a):
    tardia = '<span class="tardia">Ingresó fuera de horario</span>' if a.get("tardia") else ""
    quien = escape(a["empresa"]) + (f", enviada por el líder {escape(a['lider'])}" if a["lider"] else "")

    return f"""
    <article class="lamina" data-edad="{_clase_edad(a['edad'])}" data-p="{escape(a['proyecto'])}" data-id="{escape(a['id'])}">
      <div class="marca"><input type="checkbox" value="{escape(a['id'])}" aria-label="Seleccionar {escape(a['rubro'])}"></div>
      <div>
        <h2 class="rubro">{escape(a['rubro'])}</h2>
        <p class="quien-contrata">{quien} {tardia}</p>
        <dl class="datos">
          <div><dt>Proyecto</dt><dd>{escape(a['proyecto']) or '—'}</dd></div>
          <div><dt>Líder</dt><dd>{escape(a['lider']) or '—'}</dd></div>
          <div><dt>Monto con IVA</dt><dd>{escape(a['monto'])}</dd></div>
          <div><dt>Fecha del punto de acta</dt><dd>{escape(a['fecha'])}</dd></div>
        </dl>
      </div>
      <div class="lado"><span class="edad" data-n="{_clase_edad(a['edad'])}">{_texto_edad(a['edad'])}</span>
        <a class="btn-sec" href="/gerente/documento/{escape(a['id'])}" target="_blank" rel="noopener">Ver documento</a></div>
    </article>"""


_JS = """
<script>
  var lams = [].slice.call(document.querySelectorAll('.lamina'));
  var chips = [].slice.call(document.querySelectorAll('.chip'));
  var proyecto = '', texto = '';
  function aplicar(){
    lams.forEach(function(l){
      var okP = !proyecto || l.dataset.p === proyecto;
      var okT = !texto || l.textContent.toLowerCase().indexOf(texto) > -1;
      l.hidden = !(okP && okT);
    });
    actualizar();
  }
  chips.forEach(function(c){ c.onclick = function(){
    chips.forEach(function(x){ x.setAttribute('aria-pressed','false'); }); c.setAttribute('aria-pressed','true');
    proyecto = c.dataset.p; aplicar(); }; });
  var q = document.getElementById('q'); if (q) q.oninput = function(e){ texto = e.target.value.trim().toLowerCase(); aplicar(); };
  var todas = document.getElementById('todas');
  if (todas) todas.onchange = function(e){ lams.forEach(function(l){ if(!l.hidden){ l.querySelector('input').checked = e.target.checked; } }); actualizar(); };
  lams.forEach(function(l){
    var cb = l.querySelector('input');
    cb.onchange = actualizar;
    l.addEventListener('click', function(e){
      if (e.target.closest('a, button, input')) return;
      cb.checked = !cb.checked; actualizar();
    });
  });
  function seleccion(){ return lams.filter(function(l){ return !l.hidden && l.querySelector('input').checked; }); }
  function actualizar(){
    var s = seleccion(), vacia = s.length === 0;
    lams.forEach(function(l){ l.classList.toggle('sel', l.querySelector('input').checked); });
    document.getElementById('accion').classList.toggle('vacia', vacia);
    document.getElementById('cuenta-t').textContent = vacia ? 'Seleccione una o más actas para firmar' : s.length + (s.length === 1 ? ' acta seleccionada' : ' actas seleccionadas');
    document.getElementById('cuenta-a').textContent = vacia ? 'Marque la casilla o toque la fila.' : 'Siguiente: dibuje su firma y confirme.';
    document.getElementById('abrir').disabled = vacia;
    document.getElementById('abrir').textContent = vacia ? 'Firmar' : (s.length === 1 ? 'Firmar 1 acta' : 'Firmar ' + s.length + ' actas');
    document.getElementById('n-firmar').textContent = s.length + (s.length === 1 ? ' acta' : ' actas');
  }
  var hoja = document.getElementById('hoja'), velo = document.getElementById('velo');
  function abrir(){ if (!seleccion().length) return; hoja.classList.add('abierta'); velo.classList.add('abierto'); preparar(); }
  function cerrar(){ hoja.classList.remove('abierta'); velo.classList.remove('abierto'); }
  document.getElementById('abrir').onclick = abrir;
  document.getElementById('cerrar').onclick = cerrar; velo.onclick = cerrar;
  document.addEventListener('keydown', function(e){ if(e.key === 'Escape') cerrar(); });

  var pad = document.getElementById('pad'), ctx, dibujando = false, hay = false, subida = '';
  function preparar(){
    var r = pad.getBoundingClientRect(), d = window.devicePixelRatio || 1;
    pad.width = r.width * d; pad.height = r.height * d; ctx = pad.getContext('2d');
    ctx.scale(d, d); ctx.lineWidth = 2; ctx.lineCap = 'round'; ctx.strokeStyle = '#1B2733'; hay = false; subida = ''; verificar();
  }
  function p(e){ var r = pad.getBoundingClientRect(), t = e.touches ? e.touches[0] : e; return {x:t.clientX - r.left, y:t.clientY - r.top}; }
  function ini(e){ dibujando = true; hay = true; subida = ''; var q = p(e); ctx.beginPath(); ctx.moveTo(q.x, q.y); e.preventDefault(); verificar(); }
  function mov(e){ if(!dibujando) return; var q = p(e); ctx.lineTo(q.x, q.y); ctx.stroke(); e.preventDefault(); }
  function fin(){ dibujando = false; }
  pad.addEventListener('mousedown', ini); pad.addEventListener('mousemove', mov); window.addEventListener('mouseup', fin);
  pad.addEventListener('touchstart', ini, {passive:false}); pad.addEventListener('touchmove', mov, {passive:false}); pad.addEventListener('touchend', fin);
  document.getElementById('borrar').onclick = function(){ var r = pad.getBoundingClientRect(); ctx.clearRect(0,0,r.width,r.height); hay = false; subida = ''; document.getElementById('archivo').value = ''; verificar(); };
  document.getElementById('archivo').onchange = function(e){
    var f = e.target.files[0]; if (!f) return; var rd = new FileReader();
    rd.onload = function(){ subida = rd.result; hay = true; var r = pad.getBoundingClientRect(); ctx.clearRect(0,0,r.width,r.height);
      var im = new Image(); im.onload = function(){ var k = Math.min(r.width / im.width, (r.height - 50) / im.height); ctx.drawImage(im, 12, 8, im.width * k, im.height * k); }; im.src = subida; verificar(); };
    rd.readAsDataURL(f); };
  document.getElementById('confirma').onchange = verificar;
  function verificar(){ document.getElementById('enviar').disabled = !(hay && document.getElementById('confirma').checked); }

  document.getElementById('firmaForm').onsubmit = function(e){
    var s = seleccion(); if (!s.length || !hay) { e.preventDefault(); return; }
    document.getElementById('sig').value = subida || pad.toDataURL('image/png');
    var cont = document.getElementById('ids'); cont.innerHTML = '';
    s.forEach(function(l){ var i = document.createElement('input'); i.type = 'hidden'; i.name = 'item_ids'; i.value = l.dataset.id; cont.appendChild(i); });
    var b = document.getElementById('enviar'); b.disabled = true; b.textContent = 'Firmando...';
  };
  actualizar();
</script>
"""


def pagina_pendientes(sesion, actas):
    proyectos = {}
    for a in actas:
        proyectos[a["proyecto"]] = proyectos.get(a["proyecto"], 0) + 1

    if actas:
        chips = f'<button class="chip" aria-pressed="true" data-p="">Todas ({len(actas)})</button>' + "".join(
            f'<button class="chip" aria-pressed="false" data-p="{escape(p)}">{escape(p or "Sin proyecto")} ({n})</button>'
            for p, n in sorted(proyectos.items())
        )
        cuerpo = f"""
  <div class="filtros" role="group" aria-label="Filtrar actas">
    <input class="buscar" id="q" type="search" placeholder="Buscar rubro o contratista" aria-label="Buscar">
    {chips}
    <label class="todas"><input type="checkbox" id="todas"> Seleccionar las visibles</label>
  </div>
  <div id="lista">{''.join(_lamina(a) for a in actas)}</div>"""
        extra = """
<div class="accion vacia" id="accion"><div class="accion-in">
  <p id="cuenta"><span id="cuenta-t">Seleccione una o más actas para firmar</span><span class="ayuda" id="cuenta-a">Marque la casilla o toque la fila.</span></p>
  <button class="btn-firmar" id="abrir" disabled>Firmar</button>
</div></div>
<div class="velo" id="velo"></div>
<section class="hoja" id="hoja" role="dialog" aria-modal="true" aria-labelledby="t-hoja">
  <button class="cerrar" id="cerrar" aria-label="Cerrar">&times;</button>
  <form id="firmaForm" method="post" action="/gerente/firmar">
    <h2 id="t-hoja">Firmar <span id="n-firmar">0 actas</span></h2>
    <p class="sub">Su firma se coloca en cada documento seleccionado y pasan al siguiente paso de aprobación.</p>
    <div class="caja-firma">
      <canvas id="pad" aria-label="Área para dibujar su firma"></canvas><div class="linea"></div>
      <div class="pie"><span>FIRMA - Gerente de proyecto</span>
        <span><label for="archivo">Subir imagen</label><input type="file" id="archivo" accept="image/*" hidden> &nbsp; <button type="button" id="borrar">Borrar</button></span></div>
    </div>
    <label class="confirma"><input type="checkbox" id="confirma" name="confirmar" value="1"><span>Revisé los documentos seleccionados y apruebo su contenido.</span></label>
    <input type="hidden" name="signature_data_url" id="sig"><span id="ids"></span>
    <button class="btn-firmar" id="enviar" disabled>Firmar actas</button>
  </form>
</section>""" + _JS
    else:
        cuerpo = '<div class="vacio">Cuando el líder le envíe un acta para firmar, la verá aquí.</div>'
        extra = ""

    return _documento("Actas por firmar", _barra(sesion) + f"""
<main>
  <h1>Actas por firmar</h1>
  <p class="resumen">{escape(_resumen(actas))}</p>
  {cuerpo}
</main>{extra}""")


def pagina_trabajo(job_id):
    return _documento("Firmando actas", _barra() + f"""
<div class="tarjeta"><div class="caja">
  <h1>Firmando actas</h1>
  <p style="color:var(--tinta-2);margin:0">Cada acta tarda unos segundos. No cierre esta página hasta que termine.</p>
  <ul class="proceso" id="lista"></ul>
  <p id="fin" hidden style="margin:18px 0 0"><a href="/gerente/pendientes">Volver a mis actas pendientes</a></p>
</div></div>
<script>
  var texto = {{pendiente:'En espera', firmando:'Firmando...', firmado:'Firmada', error:'No se pudo firmar'}};
  function esc(s){{ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;'); }}
  function pintar(d){{
    document.getElementById('lista').innerHTML = d.items.map(function(i){{
      var cls = i.estado === 'firmado' ? 'ok' : (i.estado === 'error' ? 'err' : 'trabajando');
      var msg = i.mensaje ? ' (' + esc(i.mensaje) + ')' : '';
      return '<li><span>' + esc(i.nombre) + '</span><span class="' + cls + '">' + texto[i.estado] + msg + '</span></li>';
    }}).join('');
    if (d.done) document.getElementById('fin').hidden = false;
    return d.done;
  }}
  function ciclo(){{
    fetch('/gerente/trabajo/{escape(job_id)}/estado').then(function(r){{return r.json();}}).then(function(d){{
      if (!pintar(d)) setTimeout(ciclo, 2500);
    }}).catch(function(){{ setTimeout(ciclo, 4000); }});
  }}
  ciclo();
</script>""")
