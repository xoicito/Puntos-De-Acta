# Agregar cerca de los imports de app.py:
from acta_routes import acta_bp

# Agregar inmediatamente después de crear app = Flask(__name__):
app.register_blueprint(acta_bp)
