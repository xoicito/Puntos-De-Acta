"""Crea, de un solo jalon, las columnas multi-select en Monday para los 10
rubros nuevos que ya tienen plantilla oficial de Punto de Acta pero
todavia no tienen una pregunta en el formulario (Cortinas Metalicas,
Enlaminado, Canal y Flashing, ACM, Alquiler de Grua + Operador, Bomba y
Colocacion de Concreto, Puertas de Madera, Elevadores, Pozo Mecanico,
Pilotes + Nailing).

Uso:
    1. Configura MONDAY_TOKEN (variable de entorno) con el token real.
    2. python create_rubro_columns.py           -> solo muestra que va a crear
    3. python create_rubro_columns.py --yes     -> crea las columnas de verdad

Al terminar, imprime el snippet listo para pegar en config.py
(COLUMN_ALIASES) con los IDs reales que Monday asigno a cada columna.
"""

import sys

from config import ACTA_BOARD_ID
from utils.monday_client import create_column

RUBROS_NUEVOS = [
    (
        "cortinas_metalicas",
        "Cortinas Metálicas",
        [
            "Medidas y ajuste correcto",
            "Funcionamiento de apertura/cierre",
            "Motor y controles",
            "Guías rieles y poleas",
            "Anclajes correctos",
            "Seguridad operativa",
            "Lubricación y ajuste",
            "Limpieza final",
            "Sellos y sensores",
            "Acabado sin daños",
            "Otros",
        ],
    ),
    (
        "enlaminado",
        "Enlaminado",
        [
            "Alineación y nivelación",
            "Solapes y sellados",
            "Acabado sin daños",
            "Material según especificación",
            "Fijaciones correctas",
            "Drenaje funcional",
            "Anticorrosivo aplicado",
            "Limpieza final",
            "Otros",
        ],
    ),
    (
        "canal_flashing",
        "Canal y Flashing",
        [
            "Instalación correcta de canaletas",
            "Pendientes para drenaje",
            "Sellados sin filtraciones",
            "Anclajes y fijaciones",
            "Material según especificación",
            "Solapes correctos",
            "Acabado sin daños",
            "Limpieza final",
            "Otros",
        ],
    ),
    (
        "acm",
        "ACM",
        [
            "Medidas y cortes precisos",
            "Nivelación y alineación",
            "Anclajes correctos",
            "Uniones y sellados",
            "Acabado sin daños",
            "Ventilación y dilatación",
            "Limpieza final",
            "Accesibilidad para mantenimiento",
            "Otros",
        ],
    ),
    (
        "alquiler_grua",
        "Alquiler de Grúa + Operador",
        [
            "Documentación del operador",
            "Mantenimiento vigente",
            "Seguros actualizados",
            "Revisión física y mecánica del equipo",
            "Pruebas de maniobras",
            "Seguridad industrial",
            "Condiciones climáticas seguras",
            "Otros",
        ],
    ),
    (
        "bomba_concreto",
        "Bomba y Colocación de Concreto",
        [
            "Bomba en buen estado",
            "Capacidad conforme a requerimiento",
            "Pruebas de funcionamiento",
            "Concreto según especificación",
            "Nivelación y distribución",
            "Acabado final aprobado",
            "Limpieza final",
            "Anticipación de instalación",
            "Otros",
        ],
    ),
    (
        "puertas_madera",
        "Puertas de Madera",
        [
            "Medidas y ajuste en marco",
            "Herrajes funcionando",
            "Acabado y barniz",
            "Funcionamiento y alineación",
            "Sellado perimetral",
            "Anclajes y estabilidad",
            "Limpieza final",
            "Sin deformaciones",
            "Otros",
        ],
    ),
    (
        "elevadores",
        "Elevadores",
        [
            "Instalación según normativa",
            "Pruebas de funcionamiento con carga",
            "Acabados de cabina",
            "Sistemas de emergencia y seguridad",
            "Nivelación por piso",
            "Cables y poleas de tracción",
            "Botoneras y señalización",
            "Documentación técnica",
            "Eficiencia y confort",
            "Acceso para mantenimiento",
            "Otros",
        ],
    ),
    (
        "pozo_mecanico",
        "Pozo Mecánico",
        [
            "Dimensiones según planos",
            "Entubado y sellos",
            "Pruebas de caudal y bombeo",
            "Estabilidad de paredes",
            "Drenaje funcional",
            "Documentación técnica",
            "Calidad del agua",
            "Otros",
        ],
    ),
    (
        "pilotes_nailing",
        "Pilotes + Nailing",
        [
            "Ubicación y profundidad según planos",
            "Refuerzo y concreto",
            "Estabilidad de taludes y drenaje",
            "Anclajes y tensores",
            "Sin fisuras ni desplazamientos",
            "Contacto con subestructura",
            "Compactación y limpieza",
            "Otros",
        ],
    ),
]


def main():
    confirm = "--yes" in sys.argv

    print(f"Board destino: {ACTA_BOARD_ID}")
    print(f"Columnas a crear: {len(RUBROS_NUEVOS)}")
    print()

    if not confirm:
        for field, title, labels in RUBROS_NUEVOS:
            print(f"[SIMULACION] Crearia columna '{title}' ({field}) con {len(labels)} opciones:")
            print("   " + ", ".join(labels))
            print()
        print("Nada se creo todavia. Corre con --yes para crear las columnas de verdad:")
        print("   python create_rubro_columns.py --yes")
        return

    print("Creando columnas en Monday...\n")
    results = []

    for field, title, labels in RUBROS_NUEVOS:
        column_id = create_column(ACTA_BOARD_ID, title, labels)
        results.append((field, title, column_id))
        print(f"OK: '{title}' -> {column_id}")

    print("\nListo. Pega esto en config.py (COLUMN_ALIASES), reemplazando las")
    print("lineas correspondientes:\n")

    for field, title, column_id in results:
        print(f'    "{field}": ["{column_id}"],')


if __name__ == "__main__":
    main()
