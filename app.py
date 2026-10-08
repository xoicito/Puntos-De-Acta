import os

from flask import Flask, jsonify, send_file

from acta_routes import acta_bp
from firma_gerente_routes import firma_gerente_bp
from gerente_portal import gerente_portal_bp


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB - plenty for a signature image
app.register_blueprint(acta_bp)
app.register_blueprint(firma_gerente_bp)
app.register_blueprint(gerente_portal_bp)


def _es_api():
    from flask import request
    return request.path.startswith(("/webhook", "/internal"))


@app.errorhandler(404)
def pagina_no_encontrada(error):
    if _es_api():
        return error
    from gerente_portal_ui import pagina_error
    return pagina_error("La página que busca no existe o el enlace ya no es válido."), 404


@app.errorhandler(500)
def pagina_con_error(error):
    if _es_api():
        return error
    from gerente_portal_ui import pagina_error
    return pagina_error("Ocurrió un error inesperado. Intente de nuevo en un momento."), 500


@app.get("/")
def health_check():
    return jsonify(
        {
            "status": "ok",
            "service": "Puntos de Acta E4",
        }
    )


@app.get("/plantilla-alcance-cotizacion")
def plantilla_alcance_cotizacion():
    """Direct download link for the Lider to fill and upload back as their
    Alcance de Cotizacion - linked from that question's description in the
    Monday form."""
    return send_file(
        "templates/PLANTILLA_ALCANCE_COTIZACION.xlsx",
        as_attachment=True,
        download_name="PLANTILLA_ALCANCE_COTIZACION.xlsx",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
