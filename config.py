import os

MONDAY_API_URL = "https://api.monday.com/v2"
MONDAY_FILE_URL = "https://api.monday.com/v2/file"
MONDAY_API_VERSION = os.getenv("MONDAY_API_VERSION", "2026-01")
MONDAY_TOKEN = os.getenv("MONDAY_TOKEN", "")
ACTA_BOARD_ID = int(os.getenv("ACTA_BOARD_ID", "18429803408"))
ACTA_TEMPLATE = os.getenv("ACTA_TEMPLATE", "templates/100_PUNTO_DE_ACTA_PLANTILLA.xlsx")
ACTA_OUTPUT_DIR = os.getenv("ACTA_OUTPUT_DIR", "/tmp/puntos_acta")
ACTA_XLSX_COLUMN_ID = os.getenv("ACTA_XLSX_COLUMN_ID", "")
ACTA_PDF_COLUMN_ID = os.getenv("ACTA_PDF_COLUMN_ID", "")
ACTA_STATUS_COLUMN_ID = os.getenv("ACTA_STATUS_COLUMN_ID", "estado_10")
ACTA_TRIGGER_LABEL = os.getenv("ACTA_TRIGGER_LABEL", "Generar")

# IDs del board actual. Se aceptan alias de la versión anterior para facilitar migraciones.
COLUMN_ALIASES = {
    "proyecto": ["short_textgd8bvdab", "dropdown_mm6z545g"],
    "rubro": ["dropdown_mm6z1ghm", "short_textprskoevj", "dropdown_mm6zg6a9"],
    "no_contrato": ["short_text4mhsudnr", "text_mm6zdt3q"],
    "tipo_contrato": ["dropdown_mm6zs4b6", "single_selectx8edjlf", "dropdown_mm6zhe47"],
    "fecha_acta": ["datey7gu64nb", "date_mm6zrqxn"],
    "empresa": ["short_textll93jrb8", "text_mm6z1hdy"],
    "contacto": ["short_textqmmb6nuk", "text_mm6z4d0y"],
    "telefono": ["short_text30bpngci", "text_mm6z9m36"],
    "correo": ["short_textxcbqqjll", "text_mm6z8he8"],
    "nit": ["short_textxs4n6m4r", "text_mm6z1r2x"],
    "rtu": ["short_text5xsjcbmx", "text_mm6z9r0n"],
    "no_cotizacion": ["short_textnkdiu9wl", "text_mm6z81he"],
    "cotizacion": ["fileiu8wo017", "file_mm6zt2rs", "file_mm6zed6v"],
    "moneda": ["single_selectcrpolrn"],
    "anticipo": ["numeric_mm6zywyp", "short_textutqykwvo", "numeric_mm6zgmfv"],
    "estimaciones": ["numeric_mm6zdq6z", "short_text80nbowy8", "numeric_mm6zd1c6"],
    "contra_entrega": ["numeric_mm6zjs66", "short_textvvf82xfb", "numeric_mm6zj65b"],
    "retenido": ["numeric_mm6znatn", "short_text5h7ohigh", "numeric_mm6zj3gq"],
    "trabajos_previos": ["short_text2kl0cen0", "long_text_mm6z536e"],
    "servicios_basicos": ["dropdown_mm6zmjj0", "multi_selectwd6nkr5w", "dropdown_mm6z5pp1"],
    "otro_servicio_basico": ["short_text1uon0zlm", "text_mm6zhxm8"],
    "condiciones_especiales": ["long_text_mm6zx1hp", "long_text5iqaoat6", "long_text_mm6zfxx9"],
}
SUBITEM_COLUMNS = {"fecha_inicio": "fecha0", "fecha_fin": "fecha__1", "observaciones": "texto"}
