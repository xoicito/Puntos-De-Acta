import re

from config import ACTA_ESQUEMA_PAGO_COLUMN_ID, COLUMN_ALIASES
from utils.monday_client import update_text_column

CAMPOS = ("anticipo", "estimaciones", "contra_entrega", "retenido")


def _numero(texto):
    n = float(texto.replace(",", "."))

    return str(int(n)) if n == int(n) else str(n)


def porcentajes_de_esquema(etiqueta):
    """Los cuatro porcentajes (anticipo, estimaciones, contra entrega, retenido)
    escritos en la etiqueta del esquema, en ese orden - ej. "Anticipo 30% -
    Estimaciones 60% - Contra entrega 10% - Retenido 0%" o "30 / 60 / 10 / 0".
    Devuelve None si la etiqueta no trae exactamente cuatro numeros (ej.
    "Otro"), en cuyo caso se usan los porcentajes escritos a mano."""

    numeros = re.findall(r"\d+(?:[.,]\d+)?", etiqueta or "")

    if len(numeros) != 4:
        return None

    return dict(zip(CAMPOS, (_numero(n) for n in numeros)))


def aplicar_esquema_pago(data):
    """Si el formulario trae un esquema de pago elegido, sus porcentajes
    reemplazan a los escritos a mano. Sin esquema (o con "Otro", sin numeros)
    devuelve `data` tal cual. La validacion de que sumen 100% sigue aparte."""

    if not ACTA_ESQUEMA_PAGO_COLUMN_ID:
        return data

    porcentajes = porcentajes_de_esquema(data.get("esquema_pago"))

    if porcentajes is None:
        return data

    data = dict(data)
    data.update(porcentajes)
    print(f"ESQUEMA_PAGO: '{data.get('esquema_pago')}' -> {porcentajes}")

    return data


def escribir_en_item(item_id, board_id, original, nuevo):
    """Escribe los porcentajes en las columnas del item, porque otras partes
    (Control de Facturas lee el anticipo de ahi) las usan directo."""

    for campo in CAMPOS:
        valor = (nuevo.get(campo) or "").strip()

        if not valor or valor == (original.get(campo) or "").strip():
            continue

        columnas = COLUMN_ALIASES.get(campo) or []

        if not columnas:
            continue

        try:
            update_text_column(item_id, board_id, columnas[0], valor)
        except Exception as e:
            print(f"ESQUEMA_PAGO: no se pudo escribir {campo} en el item {item_id}: {e}")
