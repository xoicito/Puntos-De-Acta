import os

from flask import Flask, jsonify

from acta_routes import acta_bp
from firma_gerente_routes import firma_gerente_bp


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB - plenty for a signature image
app.register_blueprint(acta_bp)
app.register_blueprint(firma_gerente_bp)


@app.get("/")
def health_check():
    return jsonify(
        {
            "status": "ok",
            "service": "Puntos de Acta E4",
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
