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

# Alcance de Cotizacion: el Lider sube una copia llena de
# templates/PLANTILLA_ALCANCE_COTIZACION.xlsx a esta columna (tipo
# archivo, "Alcance Cotizacion") en el board principal, en lugar de
# capturar renglones en un board aparte.
COTIZACION_FILE_COLUMN_ID = os.getenv("COTIZACION_FILE_COLUMN_ID", "filezsaxj0qk")

# Board de Aprobación (firma de Arq. Melissa Alvarenga)
FIRMA_BOARD_ID = int(os.getenv("FIRMA_BOARD_ID", "18419366411"))
FIRMA_ESTADO_COLUMN_ID = os.getenv("FIRMA_ESTADO_COLUMN_ID", "color_mm4t50")
FIRMA_TRIGGER_LABEL = os.getenv("FIRMA_TRIGGER_LABEL", "FIRMADO")
FIRMA_PA_EDITABLE_COLUMN_ID = os.getenv("FIRMA_PA_EDITABLE_COLUMN_ID", "file_mm4vcga3")
FIRMA_PA_FIRMADO_COLUMN_ID = os.getenv("FIRMA_PA_FIRMADO_COLUMN_ID", "file_mm7936qy")
FIRMA_PLACEHOLDER = os.getenv("FIRMA_PLACEHOLDER", "{{FIRMA_MELISSA}}")
MELISSA_SIGNATURE_PATH = os.getenv("MELISSA_SIGNATURE_PATH", "assets/firma_melissa.jpg")

# Firma del Lider de Proyecto en el documento generado - igual que las de
# Gerente y Melissa, se ubica buscando este texto en la plantilla (celda o
# rango combinado) en vez de una coordenada fija, para que sobreviva a
# cualquier fila que se inserte arriba (ej. renglones extra de cotizacion).
LIDER_FIRMA_PLACEHOLDER = os.getenv("LIDER_FIRMA_PLACEHOLDER", "{{FIRMA_LIDER}}")

# Notificados dentro de Monday (actividad del item) cuando Arq. Melissa
# Alvarenga firma. El correo real a estas mismas personas se maneja aparte,
# con una automatizacion de Monday (destinatarios fijos, no depende de
# ninguna columna) - no necesita codigo.
FIRMA_NOTIFICAR_NOMBRES = [
    n.strip()
    for n in os.getenv(
        "FIRMA_NOTIFICAR_NOMBRES", "Allan Montenegro,Julio Tobar"
    ).split(",")
    if n.strip()
]

MULTAS_COLUMN_ID = os.getenv("MULTAS_COLUMN_ID", "multi_select278mnjmn")

# Interruptor temporal para pruebas: cuando esta en "true", se genera el
# documento normalmente pero se omite el envio del enlace de firma al
# Gerente (y por lo tanto tambien todo lo que depende de que el Gerente
# firme - el paso a Procurement, Melissa, Allan y Julio - ya que nada de
# eso ocurre sin ese enlace). Util para mostrar el formulario/documento
# sin notificar a nadie real. Dejar en "false" (o sin configurar) en uso
# normal.
TEST_MODE_SKIP_NOTIFICATIONS = os.getenv("TEST_MODE_SKIP_NOTIFICATIONS", "false").strip().lower() == "true"

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
# Columna Connect Boards en el board principal = board_relation_mm7apess
# ("BASE DATOS GERENTES") - YA NO SE USA para resolver al Gerente (ver
# GERENTE_NOMBRE_COLUMN_ID mas abajo), Monday no soporta Connect Boards en
# formularios publicos. Se deja configurada por si se usa el flujo manual
# (Opcion B: elegir el Gerente entrando al item directo en el board).
GERENTE_CONNECT_COLUMN_ID = os.getenv("GERENTE_CONNECT_COLUMN_ID", "board_relation_mm7apess")
GERENTES_BOARD_ID = int(os.getenv("GERENTES_BOARD_ID", "18431719434"))
GERENTE_EMAIL_COLUMN_ID = os.getenv("GERENTE_EMAIL_COLUMN_ID", "text_mm7ayzbv")  # board "Gerentes"
# Columna de estado/dropdown en el board principal donde el Lider elige el
# NOMBRE del Gerente (opciones fijas, mantenidas a mano igual que
# "Plantilla") - reemplaza a GERENTE_CONNECT_COLUMN_ID para el formulario.
# El correo se resuelve buscando ese nombre en GERENTES_BOARD_ID
# (find_item_by_name), no por conexion.
GERENTE_NOMBRE_COLUMN_ID = os.getenv("GERENTE_NOMBRE_COLUMN_ID", "single_select1bxlj8p")  # "Gerente"
GERENTE_FIRMA_LINK_COLUMN_ID = os.getenv("GERENTE_FIRMA_LINK_COLUMN_ID", "text_mm7aftw0")  # "Gerente Firma Link"
# Correo real del Gerente, resuelto por Connect Boards y escrito aqui para
# que la automatizacion de Monday lo use como destinatario - una columna
# Reflejo no sirve para esto, Monday no la acepta como destinatario dinamico
# en la automatizacion de enviar correo (confirmado probandolo con el PMO).
GERENTE_EMAIL_LINK_COLUMN_ID = os.getenv("GERENTE_EMAIL_LINK_COLUMN_ID", "text_mm7ewxvw")  # "Gerente Correo"
GERENTE_FIRMA_ESTADO_COLUMN_ID = os.getenv("GERENTE_FIRMA_ESTADO_COLUMN_ID", "color_mm7a8c8q")  # "Firmado?"
# TODO: confirmar las etiquetas reales de "Firmado?" - asumiendo Pendiente/Firmado,
# pero si es un status Si/No hay que ajustar estos dos valores para que coincidan.
GERENTE_FIRMA_ESTADO_PENDIENTE = os.getenv("GERENTE_FIRMA_ESTADO_PENDIENTE", "Pendiente")
GERENTE_FIRMA_ESTADO_FIRMADO = os.getenv("GERENTE_FIRMA_ESTADO_FIRMADO", "Firmado")
GERENTE_FIRMA_PLACEHOLDER = os.getenv("GERENTE_FIRMA_PLACEHOLDER", "{{FIRMA_GERENTE}}")

# PMO: el Lider lo elige por separado, en un board propio "Base Datos PMO"
# (18432219741). No firma nada - el correo se manda hasta que Melissa
# firma, no cuando el Gerente firma. Como el item que se crea en el board
# de Aprobacion no tiene la seleccion de PMO (esa vive en el item original
# del board principal), el correo del PMO se resuelve en el momento en que
# el Gerente firma (unica vez que el codigo tiene ambos items a mano) y se
# copia a PMO_EMAIL_APROBACION_COLUMN_ID en el item nuevo de Aprobacion.
# Una automatizacion de Monday ahi (disparada cuando ESTADO DE APROBACION
# cambia a FIRMADO, igual que la de Melissa) manda el correo a la
# direccion que ya quedo en esa columna. Debe ser una columna de texto
# normal - no una columna Reflejo, esa es de solo lectura para el codigo.
#
# PMO_CONNECT_COLUMN_ID YA NO SE USA para resolver al PMO (mismo motivo
# que GERENTE_CONNECT_COLUMN_ID - Connect Boards no funciona en
# formularios publicos); se deja configurada por si se usa el flujo
# manual. PMO_NOMBRE_COLUMN_ID es la columna de estado/dropdown que la
# reemplaza para el formulario.
PMO_CONNECT_COLUMN_ID = os.getenv("PMO_CONNECT_COLUMN_ID", "board_relation_mm7ea612")
PMO_BOARD_ID = int(os.getenv("PMO_BOARD_ID", "18432219741"))
PMO_NOMBRE_COLUMN_ID = os.getenv("PMO_NOMBRE_COLUMN_ID", "single_selectd8eed12")  # "PMO"
PMO_EMAIL_COLUMN_ID = os.getenv("PMO_EMAIL_COLUMN_ID", "text_mm7ayzbv")  # "e-mail" en "Base Datos PMO"
PMO_EMAIL_APROBACION_COLUMN_ID = os.getenv("PMO_EMAIL_APROBACION_COLUMN_ID", "")

# Debe ser un valor fijo y secreto (no lo genere al azar en cada arranque -
# eso invalidaria todos los enlaces pendientes en cada despliegue). Config
# en Render como variable de entorno real, nunca en el codigo.
GERENTE_LINK_SECRET_KEY = os.getenv("GERENTE_LINK_SECRET_KEY", "")
GERENTE_LINK_BASE_URL = os.getenv("GERENTE_LINK_BASE_URL", "https://puntos-de-acta.onrender.com")

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
    "gerente_proyecto": [GERENTE_NOMBRE_COLUMN_ID, "short_textlyk3dimh", GERENTE_CONNECT_COLUMN_ID],
    "acta_id": ["text_mm736ka4"],
    "multas_aplicar": [MULTAS_COLUMN_ID],
    "multa_atraso_monto": ["short_textjv7r1s2w"],  # "Multa por atraso de entrega"
    "multa_orden_monto": ["short_textt2l4xfsm"],  # "Multa por orden y limpieza"
    "multa_seguridad_monto": ["short_textih9093ma"],  # "Multa por incumplimiento de Seguridad Industrial"
    "multa_reporteria_monto": ["short_texthyqsd3r3"],  # "Multa por incumplimiento de reportería semanal"
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
    # aac/sci/mobiliario each have an orphaned duplicate column on the board
    # (multi_select2kmk23ve, multi_selectics6jahz, multi_selectehkiwsw3 -
    # not on the live form) - confirmed against the actual form 2026-09-21,
    # do not swap back to those.
    "aac": ["multi_selectq09u0es1"],
    "sci": ["multi_select4wdu7jby"],
    "carpinteria": ["multi_select9nnochog"],
    "mobiliario": ["multi_selectzqvpeduy"],
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
    "trabajos_previos": ["long_textbzq1myqd", "short_text2kl0cen0"],
    "servicios_basicos": ["dropdown_mm6zmjj0", "multi_selectwd6nkr5w", "dropdown_mm6z5pp1"],
    "otro_servicio_basico": ["short_text1uon0zlm", "text_mm6zhxm8"],
        "puntos_generales": [
        "multi_selectyys0fxzb"
    ],

    "planos_entregados": [
        "multi_selecthrnfdufd"
    ],

    "cortinas_metalicas": ["dropdown_mm7a1snp"],
    "enlaminado": ["dropdown_mm7agxgw"],
    "canal_flashing": ["dropdown_mm7av5pp"],
    "acm": ["dropdown_mm7ayn6h"],
    "alquiler_grua": ["dropdown_mm7aksrb"],
    "bomba_concreto": ["dropdown_mm7a771m"],
    "puertas_madera": ["dropdown_mm7atz4c"],
    "elevadores": ["dropdown_mm7agt67"],
    "pozo_mecanico": ["dropdown_mm7adryb"],
    "pilotes_nailing": ["dropdown_mm7awz8f"],
}
SUBITEM_COLUMNS = {"fecha_inicio": "fecha0", "fecha_fin": "fecha__1", "observaciones": "texto"}
