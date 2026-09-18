"""Agrega los 10 nombres de rubros nuevos como opciones del dropdown
"Plantilla" existente (single_selectb2r025a) en el board principal.

Monday no tiene una mutacion publica para "agregar opcion a una columna
existente". El truco conocido es: en columnas tipo "status", si le
mandas un valor con una etiqueta que no existe todavia, Monday la crea
sola. Esto NO esta garantizado para columnas tipo "dropdown" (ahi las
opciones se referencian por id, no se crean solas al usar un texto
nuevo) - por eso este script primero solo CONSULTA el tipo real de la
columna, sin escribir nada, y unicamente intenta crear las etiquetas si
confirma que es tipo "status".

Uso:
    1. Configura MONDAY_TOKEN (variable de entorno).
    2. python add_plantilla_labels.py          -> solo consulta el tipo de columna y las etiquetas actuales
    3. python add_plantilla_labels.py --yes    -> intenta agregar las 10 etiquetas nuevas (solo si es tipo status)
"""

import json
import sys

from config import ACTA_BOARD_ID
from utils.monday_client import change_status, create_item, graphql

PLANTILLA_COLUMN_ID = "single_selectb2r025a"

NUEVAS_OPCIONES = [
    "Cortinas Metálicas",
    "Enlaminado",
    "Canal y Flashing",
    "ACM",
    "Alquiler de Grúa + Operador",
    "Bomba y Colocación de Concreto",
    "Puertas de Madera",
    "Elevadores",
    "Pozo Mecánico",
    "Pilotes + Nailing",
]


def get_plantilla_column():
    q = """query ($ids: [ID!]!) {
        boards(ids: $ids) {
            columns {
                id
                title
                type
                settings_str
            }
        }
    }"""

    boards = graphql(q, {"ids": [str(ACTA_BOARD_ID)]})["boards"]
    columns = boards[0]["columns"]

    for c in columns:
        if c["id"] == PLANTILLA_COLUMN_ID:
            return c

    return None


def main():
    confirm = "--yes" in sys.argv

    column = get_plantilla_column()

    if not column:
        print(f"No se encontro la columna {PLANTILLA_COLUMN_ID} en el board {ACTA_BOARD_ID}.")
        return

    print(f"Columna: {column['title']} ({column['id']})")
    print(f"Tipo real segun Monday: {column['type']}")

    try:
        settings = json.loads(column["settings_str"] or "{}")
        labels = settings.get("labels", {})
        print(f"Etiquetas actuales ({len(labels)}):")
        for k, v in labels.items():
            print(f"   {k}: {v}")
    except Exception as e:
        print(f"No se pudo leer settings_str: {e}")

    print()

    if column["type"] != "status":
        print(f"Tipo '{column['type']}' no es 'status' - el truco de auto-crear etiquetas")
        print("al asignar un valor nuevo NO esta garantizado para este tipo de columna.")
        print("No se va a intentar escribir nada. Esto necesita hacerse manualmente en Monday.")
        return

    print("Tipo 'status' confirmado - el truco deberia funcionar.")

    if not confirm:
        print("\n[SIMULACION] Crearia un item temporal y le asignaria, una por una,")
        print("las siguientes etiquetas nuevas en 'Plantilla' (para que Monday las cree),")
        print("y luego borraria el item temporal:")
        for op in NUEVAS_OPCIONES:
            print(f"   - {op}")
        print("\nNada se creo todavia. Corre con --yes para hacerlo de verdad:")
        print("   python add_plantilla_labels.py --yes")
        return

    print("\nCreando item temporal...")
    temp_item_id = create_item(ACTA_BOARD_ID, "TEMP - creando etiquetas Plantilla (borrar automaticamente)")
    print(f"Item temporal: {temp_item_id}")

    for op in NUEVAS_OPCIONES:
        change_status(temp_item_id, ACTA_BOARD_ID, PLANTILLA_COLUMN_ID, op)
        print(f"OK: etiqueta creada/asignada -> {op}")

    q_delete = """mutation ($item: ID!) {
        delete_item(item_id: $item) {
            id
        }
    }"""
    graphql(q_delete, {"item": str(temp_item_id)})
    print(f"\nItem temporal {temp_item_id} borrado.")

    print("\nListo. Verifica en Monday que las 10 etiquetas nuevas aparezcan en 'Plantilla'.")


if __name__ == "__main__":
    main()
