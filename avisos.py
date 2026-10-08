"""Avisos que el sistema calcula al generar un Punto de Acta.

No bloquean nada (el acta se genera igual): son cosas que probablemente son un
error del formulario y que conviene revisar antes de enviar al Gerente. Se dejan
como comentario en el item, y la pestana "Estado de las actas" los muestra.
"""

from datetime import datetime
from html import escape

MARCA = "Avisos del sistema"

# Titulos de los avisos, para reconocerlos en el texto del comentario.
TITULOS = (
    "La cotización no tiene renglones",
    "El total de la cotización es cero",
    "Hay renglones sin cantidad o sin precio",
    "El retenido no coincide con el 5 % impreso en el acta",
    "No hay programación de fechas",
    "La fecha de fin es anterior a la de inicio",
    "Falta el teléfono del contratista",
)


def _numero(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _fecha(texto):
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime((texto or "").strip(), formato)
        except ValueError:
            continue

    return None


def avisos_de_generacion(data, cotizacion_rows, programacion_rows, retenido_pct):
    """Lista de dicts {codigo, titulo, detalle, que_hacer}; vacia si todo se ve bien.

    `retenido_pct`: porcentaje de retenido ya convertido a numero (None si no hay)."""

    avisos = []

    if not cotizacion_rows:
        avisos.append({
            "codigo": "cotizacion_vacia",
            "titulo": "La cotización no tiene renglones",
            "detalle": "El archivo de Alcance de cotización no trae ningún renglón con datos, así que la tabla del acta quedó vacía.",
            "que_hacer": "Llene la plantilla con sus renglones y vuelva a generar el acta.",
        })
    else:
        total = sum((_numero(r.get("cantidad")) or 0) * (_numero(r.get("precio")) or 0) for r in cotizacion_rows)
        malos = [
            str(i) for i, r in enumerate(cotizacion_rows, 1)
            if (_numero(r.get("cantidad")) or 0) <= 0 or (_numero(r.get("precio")) or 0) <= 0
        ]

        if total <= 0:
            avisos.append({
                "codigo": "total_cero",
                "titulo": "El total de la cotización es cero",
                "detalle": "Los renglones no suman ningún monto.",
                "que_hacer": "Revise cantidades y precios unitarios en la plantilla y vuelva a generar el acta.",
            })
        elif malos:
            avisos.append({
                "codigo": "renglones_en_cero",
                "titulo": "Hay renglones sin cantidad o sin precio",
                "detalle": "Renglón(es) " + ", ".join(malos[:8]) + (" y más" if len(malos) > 8 else "") + " con cantidad o precio vacío o en cero.",
                "que_hacer": "Complete esos renglones en la plantilla o elimínelos, y vuelva a generar el acta.",
            })

    if retenido_pct is not None and abs(retenido_pct - 5) > 0.01:
        avisos.append({
            "codigo": "retenido_distinto",
            "titulo": "El retenido no coincide con el 5 % impreso en el acta",
            "detalle": f"El formulario indica {retenido_pct:g} % de retenido, pero el acta siempre imprime «RETENCIÓN: 5 % del monto total retenido por 3 meses».",
            "que_hacer": "Si el retenido correcto es 5 %, corríjalo en el formulario. Si es otro, avise para ajustar el texto fijo del acta.",
        })

    if not programacion_rows:
        avisos.append({
            "codigo": "programacion_vacia",
            "titulo": "No hay programación de fechas",
            "detalle": "El acta no tiene ninguna fila en Programación de fechas.",
            "que_hacer": "Agregue al menos un área con fecha de inicio y de fin y vuelva a generar el acta.",
        })
    else:
        invertidas = []

        for r in programacion_rows:
            inicio, fin = _fecha(r.get("inicio")), _fecha(r.get("fin"))

            if inicio and fin and fin < inicio:
                invertidas.append(r.get("area") or "sin nombre")

        if invertidas:
            avisos.append({
                "codigo": "fechas_invertidas",
                "titulo": "La fecha de fin es anterior a la de inicio",
                "detalle": "Revisar la programación de: " + ", ".join(invertidas[:6]) + ".",
                "que_hacer": "Corrija las fechas de esas áreas y vuelva a generar el acta.",
            })

    if not (data.get("telefono") or "").strip():
        avisos.append({
            "codigo": "sin_telefono",
            "titulo": "Falta el teléfono del contratista",
            "detalle": "El campo de teléfono quedó vacío y el acta lo imprime en blanco.",
            "que_hacer": "Escriba el teléfono en el formulario y vuelva a generar el acta.",
        })

    return avisos


def texto_de_avisos(avisos):
    """Comentario del item: HTML corto, con un encabezado fijo (MARCA) que la
    pestana de estados reconoce, y un punto por aviso con su 'que hacer'."""

    puntos = "".join(
        f"<li><b>{escape(a['titulo'])}.</b> {escape(a['detalle'])} <i>Qué hacer: {escape(a['que_hacer'])}</i></li>"
        for a in avisos
    )

    return f"<p><b>{MARCA}</b>: revise estos puntos antes de enviar el acta al Gerente.</p><ul>{puntos}</ul>"
