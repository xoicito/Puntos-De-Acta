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
ACTA_ID_COLUMN_ID = os.getenv("ACTA_ID_COLUMN_ID", "text_mm736ka4")
SIGNATURE_COLUMN_ID = os.getenv("SIGNATURE_COLUMN_ID", "file80ymdmtg")
COTIZACION_BOARD_ID = 18430739172

# Board de Aprobación (firma de Arq. Melissa Alvarenga)
FIRMA_BOARD_ID = int(os.getenv("FIRMA_BOARD_ID", "18419366411"))
FIRMA_ESTADO_COLUMN_ID = os.getenv("FIRMA_ESTADO_COLUMN_ID", "color_mm4t50")
FIRMA_TRIGGER_LABEL = os.getenv("FIRMA_TRIGGER_LABEL", "FIRMADO")
FIRMA_PA_EDITABLE_COLUMN_ID = os.getenv("FIRMA_PA_EDITABLE_COLUMN_ID", "file_mm4vcga3")
FIRMA_PA_FIRMADO_COLUMN_ID = os.getenv("FIRMA_PA_FIRMADO_COLUMN_ID", "file_mm7936qy")
FIRMA_PLACEHOLDER = os.getenv("FIRMA_PLACEHOLDER", "{{FIRMA_MELISSA}}")
MELISSA_SIGNATURE_PATH = os.getenv("MELISSA_SIGNATURE_PATH", "assets/firma_melissa.jpg")

MULTAS_COLUMN_ID = os.getenv("MULTAS_COLUMN_ID", "multi_select278mnjmn")

# Firma del Gerente de Proyecto via enlace único (no requiere sesión de Monday).
#
# Flujo: al terminar de generar el acta, se resuelve el correo real del
# Gerente a traves de un Connect Boards column ("Gerente de Proyecto" en
# el board principal) que apunta a un board "Gerentes" (un item por
# persona, con su correo). El Lider solo puede elegir entre los items que
# existan ahi - nunca escribe un correo el mismo - y el equipo puede
# agregar gerentes nuevos agregando items a ese board, sin tocar codigo.
# Se genera un enlace firmado y con expiracion, y se escribe en
# GERENTE_FIRMA_LINK_COLUMN_ID - una automatizacion de Monday (configurada
# en la UI, no en este codigo) envia el correo cuando esa columna cambia.
# Tambien se publica un update en el item para notificacion dentro de Monday.
#
# El token no se guarda en ningun lado: es un valor firmado (itsdangerous)
# que se verifica solo, y expira solo, sin base de datos nueva. Lo unico
# que se persiste es el estado "Pendiente"/"Firmado" en Monday, que sirve
# como el control de un solo uso: un token ya firmado se rechaza aunque
# todavia no haya expirado.
#
# Board "Gerentes" = 18431719434, con columna "e-mail" (text_mm7ayzbv).
# TODO: falta GERENTE_CONNECT_COLUMN_ID (columna Connect Boards en el board principal).
GERENTE_CONNECT_COLUMN_ID = os.getenv("GERENTE_CONNECT_COLUMN_ID", "")  # board principal
GERENTE_EMAIL_COLUMN_ID = os.getenv("GERENTE_EMAIL_COLUMN_ID", "text_mm7ayzbv")  # board "Gerentes"
GERENTE_FIRMA_LINK_COLUMN_ID = os.getenv("GERENTE_FIRMA_LINK_COLUMN_ID", "")
GERENTE_FIRMA_ESTADO_COLUMN_ID = os.getenv("GERENTE_FIRMA_ESTADO_COLUMN_ID", "")
GERENTE_FIRMA_ESTADO_PENDIENTE = os.getenv("GERENTE_FIRMA_ESTADO_PENDIENTE", "Pendiente")
GERENTE_FIRMA_ESTADO_FIRMADO = os.getenv("GERENTE_FIRMA_ESTADO_FIRMADO", "Firmado")
GERENTE_FIRMA_PLACEHOLDER = os.getenv("GERENTE_FIRMA_PLACEHOLDER", "{{FIRMA_GERENTE}}")

# Debe ser un valor fijo y secreto (no lo genere al azar en cada arranque -
# eso invalidaria todos los enlaces pendientes en cada despliegue). Config
# en Render como variable de entorno real, nunca en el codigo.
GERENTE_LINK_SECRET_KEY = os.getenv("GERENTE_LINK_SECRET_KEY", "")
GERENTE_LINK_BASE_URL = os.getenv("GERENTE_LINK_BASE_URL", "https://puntos-de-acta.onrender.com")
GERENTE_LINK_EXPIRATION_HOURS = int(os.getenv("GERENTE_LINK_EXPIRATION_HOURS", "72"))

# "Elegir la manera de firma del Lider de Proyecto" dropdown: "Subir PNG"
# (SIGNATURE_COLUMN_ID = file80ymdmtg) or "Dibujarla", Monday's built-in
# signing experience (FIRMA_MONDAY_COLUMN_ID = signature9vmootoj). Both
# report as plain "file" columns in the API, so the same asset-extraction
# logic (get_file_public_url) works for either.
METODO_FIRMA_COLUMN_ID = os.getenv("METODO_FIRMA_COLUMN_ID", "single_selectvkxra86")
METODO_FIRMA_MONDAY_LABEL = os.getenv("METODO_FIRMA_MONDAY_LABEL", "Dibujarla")
FIRMA_MONDAY_COLUMN_ID = os.getenv("FIRMA_MONDAY_COLUMN_ID", "signature9vmootoj")

# IDs del board actual. Se aceptan alias de la versión anterior para facilitar migraciones.
COLUMN_ALIASES = {
    "plantilla": ["single_selectb2r025a"],
    "lider_proyecto": ["short_textoea3ks5w"],
    "gerente_proyecto": ["short_textlyk3dimh", GERENTE_CONNECT_COLUMN_ID],
    "acta_id": ["text_mm736ka4"],
    "multas_aplicar": [MULTAS_COLUMN_ID],
    "metodo_firma": [METODO_FIRMA_COLUMN_ID],
    "herreria": ["multi_select3i0wzl2b"],
    "ventaneria": ["multi_selectv1jxlsfg"],
    "tabla_yeso": ["multi_selectzfz9xl7e"],
    "pintura": ["multi_selectc0iwzq3k"],
    "electricidad": ["multi_selectdbesbk2p"],
    "piso": ["multi_selectg81so7dw"],
    "cielo_falso": ["multi_selectvb0m3pot"],
    "aluminio_vidrio": ["multi_selectjxfvgjx3"],
    "hidrosanitaria": ["multi_selectqy93bkwp"],
    "aac": ["multi_select2kmk23ve"],
    "sci": ["multi_selectics6jahz"],
    "carpinteria": ["multi_select9nnochog"],
    "mobiliario": ["multi_selectehkiwsw3"],
    "mamposteria": ["multi_selectbtv82pt7"],
    "obra_civil": ["multi_selectgs2drrw0"],
    "topografia": ["multi_select08qjt1im"],
    "urbanizacion": ["multi_select8z5qf4th"],
    "cubierta": ["multi_selectqicxkoxs"],
    "impermeabilizacion": ["multi_select5lxg6w00"],
    "estructura_metalica": ["multi_selecth12dnuzk"],
    "senalizacion": ["multi_selectwztghp45"],
    "acabados": ["multi_selectyyqp6yzb"],
    "otros_revision": ["long_text175tw0mw"],
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
        "puntos_generales": [
        "multi_selectyys0fxzb"
    ],

    "planos_entregados": [
        "multi_selecthrnfdufd"
    ],
}
SUBITEM_COLUMNS = {"fecha_inicio": "fecha0", "fecha_fin": "fecha__1", "observaciones": "texto"}
