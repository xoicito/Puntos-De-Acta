from datetime import datetime
from config import COLUMN_ALIASES, SUBITEM_COLUMNS

IMMUTABLE_POINTS = [
    "CAMBIO DE PROVEEDOR: Si el proveedor no reacciona a los requerimientos solicitados previos y a los contratados, se debe cambiar no más de 3 días después de la falta de reacción.",
    "GARANTÍA: Si el proveedor tuvo un trabajo de mala calidad, se deben descontar materiales y otros gastos que se requieran.",
    "RETENCIÓN: 5% del monto total retenido por 3 meses luego de haber recibido con satisfacción los trabajos.",
    "El proveedor se compromete a cumplir con todas las normas del ACUERDO GUBERNATIVO 229-204 Y SUS REFORMAS 33-2016. De no cumplir con las normativas del acuerdo o las internas del proyecto, se podrá dar por terminado el contrato.",
]

# Default amounts, taken from the original template (cells P30-P33) - used
# whenever the corresponding multa is selected in the MULTAS_COLUMN_ID
# dropdown. Anything not selected renders as "N/A".
MULTAS_DEFAULTS = {
    "atraso": "1% POR DIA",
    "orden": "Q.25 POR EVENTO",
    "seguridad": "Q.50 POR PERSONA",
    "reporteria": "Q.25 POR EVENTO",
}

# Maps each "Multas a Aplicar" dropdown option label (lowercase) to the
# multa key it selects. Matches the exact option text configured in Monday
# (multi_select278mnjmn), accents included, plus a couple of forgiving
# fallback variants.
MULTAS_OPTION_MAP = {
    "por atraso de entrega": "atraso",
    "atraso": "atraso",
    "por órden y limpieza": "orden",
    "por orden y limpieza": "orden",
    "orden y limpieza": "orden",
    "orden": "orden",
    "por no cumplir con seguridad industrial": "seguridad",
    "seguridad industrial": "seguridad",
    "seguridad": "seguridad",
    "por no cumplir con documentos de reportería semanal": "reporteria",
    "por no cumplir con documentos de reporteria semanal": "reporteria",
    "reportería semanal": "reporteria",
    "reporteria semanal": "reporteria",
    "reporteria": "reporteria",
}

# Cada opción del multi-select del formulario (más simple, para el Líder)
# se expande a una o más líneas exactas de "Puntos de Revisión Específica"
# tomadas de la plantilla oficial de ese rubro - así el documento final
# siempre usa el texto oficial, nunca el texto corto de la opción. Solo
# cubre los rubros cuya plantilla oficial (100-117) ya se revisó línea por
# línea; los demás rubros siguen usando el texto de la opción tal cual
# (comportamiento anterior) hasta que se agregue su plantilla oficial.
PUNTOS_OPCION_MAP = {
    "herreria": {
        "soldaduras completas": [
            "Soldaduras y uniones estructurales revisadas",
        ],
        "soldaduras limpias": [
            "Limpieza final realizada, sin residuos metálicos",
        ],
        "cordones uniformes": [
            "Material utilizado según especificaciones",
            "Bordes sin filos peligrosos",
        ],
        "aplicación de anticorrosivo": [
            "Tratamientos anticorrosivos aplicados (galvanizado, pintura)",
        ],
        "aplicacion de anticorrosivo": [
            "Tratamientos anticorrosivos aplicados (galvanizado, pintura)",
        ],
        "aplicación de pintura final": [
            "Acabados bien ejecutados (lijado, pulido, pintura)",
            "Pintura o esmalte aplicado correctamente",
            "Estado final documentado y registrado",
        ],
        "aplicacion de pintura final": [
            "Acabados bien ejecutados (lijado, pulido, pintura)",
            "Pintura o esmalte aplicado correctamente",
            "Estado final documentado y registrado",
        ],
        "anclajes correctos": [
            "Mecanismos móviles funcionales (bisagras, cerraduras, ruedas)",
            "Fijaciones y anclajes seguros",
            "Pruebas de carga exitosas en elementos críticos",
            "Tornillos y remaches de seguridad instalados correctamente",
        ],
        "nivelación": [
            "Barandales y puertas nivelados y aplomados",
            "Drenaje funcional en piezas expuestas",
        ],
        "nivelacion": [
            "Barandales y puertas nivelados y aplomados",
            "Drenaje funcional en piezas expuestas",
        ],
        "plomeo": [
            "Barandales y puertas nivelados y aplomados",
        ],
        "alineación": [
            "Dimensiones y alineación conforme a planos",
            "Buena integración con otros elementos estructurales",
        ],
        "alineacion": [
            "Dimensiones y alineación conforme a planos",
            "Buena integración con otros elementos estructurales",
        ],
    },
    "ventaneria": {
        "nivelación": ["Marcos nivelados y plomados correctamente"],
        "nivelacion": ["Marcos nivelados y plomados correctamente"],
        "plomeo": ["Marcos nivelados y plomados correctamente"],
        "sellos de silicón": [
            "Burletes y sellado perimetral instalados correctamente",
        ],
        "sellos de silicon": [
            "Burletes y sellado perimetral instalados correctamente",
        ],
        "vidrios sin daños": [
            "Vidrios instalados sin daños, rayones ni burbujas",
        ],
        "vidrios sin danos": [
            "Vidrios instalados sin daños, rayones ni burbujas",
        ],
        "anclajes correctos": [
            "Fijación y anclaje realizados al soporte estructural",
            "Medidas instaladas conforme a lo cotizado",
        ],
        "limpieza final": [
            "Instalación limpia, sin residuos de sellador ni adhesivos",
        ],
        "funcionamiento de hojas móviles": [
            "Mecanismos de apertura y cierre funcionando correctamente",
        ],
        "funcionamiento de hojas moviles": [
            "Mecanismos de apertura y cierre funcionando correctamente",
        ],
        "acabados completos": [
            "Material instalado concuerda con lo cotizado",
            "Herrajes y accesorios colocados según especificación",
            "Alineación correcta con otras ventanas del proyecto",
            "Integración adecuada con acabados contiguos (pintura, yeso)",
            "Perfiles sin deformaciones visibles por instalación",
        ],
    },
    "tabla_yeso": {
        "nivelación": [
            "Paneles alineados y nivelados según diseño",
            "Nivelación verificada con láser en grandes superficies",
        ],
        "nivelacion": [
            "Paneles alineados y nivelados según diseño",
            "Nivelación verificada con láser en grandes superficies",
        ],
        "plomeo": [
            "Estructura soporte instalada correctamente (montantes y canales)",
            "Fijaciones realizadas con separación y cantidad adecuada",
            "Resistencia estructural del panel comprobada",
            "Paneles en techos suspendidos presentan estabilidad",
        ],
        "uniones tratadas": [
            "Juntas tratadas con cinta y masilla en todas las uniones",
            "Insonorización adecuada en paredes divisorias",
        ],
        "juntas lijadas": [
            "Cortes limpios realizados en esquinas, puertas y ventanas",
        ],
        "acabado uniforme": [
            "Materiales empleados cumplen con especificaciones de proyecto",
            "Integración adecuada con molduras, pisos y otros acabados",
        ],
        "ausencia de grietas": [
            "Refuerzos colocados en puntos críticos según requerimientos",
        ],
        "pintura completa": [
            "Acabado superficial sin fisuras ni imperfecciones",
        ],
        "limpieza final": [
            "Limpieza completa de polvo y residuos previo a acabado final",
        ],
    },
    "pintura": {
        "cobertura uniforme": [
            "Aplicación uniforme y con buen acabado",
            "Compatibilidad entre diferentes pinturas comprobada",
        ],
        "color correcto": [
            "Tipo y color de pintura aplicados según especificaciones",
        ],
        "sin manchas": [
            "Superficie sin escurrimientos, burbujas ni manchas",
        ],
        "sin escurrimientos": [
            "Superficie sin escurrimientos, burbujas ni manchas",
        ],
        "preparación adecuada de superficie": [
            "Adherencia comprobada satisfactoriamente",
            "Imprimantes y selladores aplicados correctamente",
            "Compatibilidad de pintura con material base verificada",
        ],
        "preparacion adecuada de superficie": [
            "Adherencia comprobada satisfactoriamente",
            "Imprimantes y selladores aplicados correctamente",
            "Compatibilidad de pintura con material base verificada",
        ],
        "acabado final aprobado": [
            "Esquinas, uniones y bordes bien detallados",
            "Textura y acabado final conforme a lo especificado (mate, satinado, brillante)",
            "Retoques realizados tras instalación de otros elementos",
        ],
        "limpieza final": [
            "Zonas no deseadas libres de residuos de pintura",
        ],
    },
    "electricidad": {
        "pruebas de funcionamiento": [
            "Continuidad y resistencia eléctrica verificadas",
            "Pruebas de carga y amperaje realizadas con éxito",
            "Luminarias instaladas y funcionando correctamente",
            "Conductores con aislamiento verificado en pruebas de resistencia",
            "Iluminación de emergencia funcional y conforme a diseño",
        ],
        "canalización correcta": [
            "Instalación realizada según planos eléctricos y normativa",
            "Canalizaciones y cajas ubicadas conforme a diseño",
            "Bandejas y canalizaciones correctamente fijadas",
            "Ductos eléctricos con integridad estructural confirmada",
        ],
        "canalizacion correcta": [
            "Instalación realizada según planos eléctricos y normativa",
            "Canalizaciones y cajas ubicadas conforme a diseño",
            "Bandejas y canalizaciones correctamente fijadas",
            "Ductos eléctricos con integridad estructural confirmada",
        ],
        "etiquetado de circuitos": [
            "Circuitos eléctricos rotulados y documentados correctamente",
        ],
        "conexiones seguras": [
            "Cableado instalado con el calibre y tipo especificado",
            "Conexiones y empalmes revisados en tableros y cajas",
            "Compatibilidad entre conductores y térmicos verificada",
            "Fases correctamente conectadas en sistemas trifásicos",
        ],
        "tableros identificados": [
            "Interruptores diferenciales presentes en tableros",
            "Protecciones contra sobretensiones instalad",
            "Dispositivos de control energético instalados correctamente",
        ],
        "voltajes correctos": [
            "Polaridad verificada en tomacorrientes y conexiones",
            "Caída de tensión dentro de rangos aceptables",
        ],
        "puesta a tierra": [
            "Puesta a tierra instalada en equipos y tableros",
        ],
        # "Limpieza final" no tiene una línea correspondiente en la
        # plantilla oficial de Electricidad (ningún punto menciona
        # limpieza) - se deja sin mapear a propósito, en vez de forzar
        # una coincidencia que no aplica.
        "limpieza final": [],
    },
}


def _values(item):
    """Extract column values from an item as a dictionary."""
    return {
        c["id"]: (c.get("text") or "").strip()
        for c in item.get("column_values", [])
    }


def _pick(values, key):
    """Pick the first available column value for a given key from COLUMN_ALIASES."""
    if key not in COLUMN_ALIASES:
        return ""

    for column_id in COLUMN_ALIASES[key]:
        if values.get(column_id):
            return values[column_id]

    return ""


def item_data(item):
    """Extract and organize item data using column aliases."""
    v = _values(item)

    data = {
        k: _pick(v, k)
        for k in COLUMN_ALIASES
    }

    data["item_id"] = str(item["id"])
    data["item_name"] = item.get("name", "")
    data["board_id"] = str(
        item.get("board", {}).get("id", "")
    )
    data["subitems"] = item.get("subitems", [])

    return data


def split_lines(text):
    """Split text into lines, removing empty ones and normalizing whitespace."""
    return [
        " ".join(x.split())
        for x in (text or "").splitlines()
        if x.strip()
    ]


def numbered(lines):
    """Convert a list of lines into a numbered list format."""
    return "\n".join(
        f"{i}. {x}"
        for i, x in enumerate(lines, 1)
    )


def pct(value):
    """Ensure a value ends with a percentage symbol."""
    value = (value or "").strip()

    return (
        value
        if not value
        or value.endswith("%")
        else value + "%"
    )


def display_date(value):
    """Convert a date string to DD/MM/YYYY format, supporting multiple input formats."""
    if not value:
        return ""

    for fmt in (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(
                value,
                fmt
            ).strftime("%d/%m/%Y")
        except ValueError:
            pass

    return value


def rubric_code(rubro):
    """Extract the rubric code (1XX pattern) from a rubric string."""
    import re

    m = re.search(
        r"\b(1\d{2})\b",
        rubro or ""
    )

    return m.group(1) if m else "100"


def build_programacion(subitems):
    """Build a list of programming entries from subitems with dates and observations."""
    rows = []

    for s in subitems:

        v = {
            c["id"]: (
                c.get("text") or ""
            ).strip()
            for c in s.get(
                "column_values",
                []
            )
        }

        area = (
            s.get("name") or ""
        ).strip()

        ini = display_date(
            v.get(
                SUBITEM_COLUMNS["fecha_inicio"],
                ""
            )
        )

        fin = display_date(
            v.get(
                SUBITEM_COLUMNS["fecha_fin"],
                ""
            )
        )

        obs = v.get(
            SUBITEM_COLUMNS["observaciones"],
            ""
        )

        if any((area, ini, fin, obs)):

            rows.append({
                "area": area,
                "inicio": ini,
                "fin": fin,
                "obs": obs,
            })

    return rows


def build_services(data):
    """Build a list of basic services from comma/semicolon-separated values."""
    values = [
        x.strip()
        for x in (
            data.get(
                "servicios_basicos"
            )
            or ""
        ).replace(
            ";",
            ","
        ).split(",")
        if x.strip()
    ]

    other = (
        data.get(
            "otro_servicio_basico",
            ""
        )
        .strip()
    )

    if (
        other
        and other.lower()
        not in {
            x.lower()
            for x in values
        }
    ):
        values.append(other)

    return values


def build_planos_entregados(data):

    selected = parse_multi(
        data.get("planos_entregados")
    )

    return {
        "arquitectura": "SI" if "arquitectura" in selected else "NO",
        "cotas": "SI" if "cotas" in selected else "NO",
        "elevaciones": "SI" if "elevaciones y secciones" in selected else "NO",
        "hidrosanitarias": "SI" if "hidrosanitarias" in selected else "NO",
        "electricidad": "SI" if "electricidad" in selected else "NO",
        "acabados": "SI" if "acabados" in selected else "NO",
        "estructura_principal": "SI" if "estructura principal" in selected else "NO",
        "estructura_secundaria": "SI" if "estructura secundaria" in selected else "NO",
        "obras_secundarias": "SI" if "obras secundarias" in selected else "NO",
    }


def build_planos(data):

    selected = parse_multi(
        data.get("planos_entregados")
    )

    return {
        "{{PL_ARQ}}":
            "SI" if "arquitectura" in selected else "NO",

        "{{PL_COTAS}}":
            "SI" if "cotas" in selected else "NO",

        "{{PL_ELEV}}":
            "SI" if "elevaciones y secciones" in selected else "NO",

        "{{PL_HIDRO}}":
            "SI" if "hidrosanitarias" in selected else "NO",

        "{{PL_ELEC}}":
            "SI" if "electricidad" in selected else "NO",

        "{{PL_ACAB}}":
            "SI" if "acabados" in selected else "NO",

        "{{PL_ESTR_PRIN}}":
            "SI" if "estructura principal" in selected else "NO",

        "{{PL_ESTR_SEC}}":
            "SI" if "estructura secundaria" in selected else "NO",

        "{{PL_OBRAS}}":
            "SI" if "obras secundarias" in selected else "NO",
    }


def build_template_points(data):

    plantilla = (
        data.get("plantilla") or ""
    ).strip().lower()

    mapping = {
        "herrería": "herreria",
        "ventanería": "ventaneria",
        "tabla yeso": "tabla_yeso",
        "pintura": "pintura",
        "electricidad": "electricidad",
        "piso": "piso",
        "cielo falso": "cielo_falso",
        "aluminio y vidrio": "aluminio_vidrio",
        "hidrosanitaria": "hidrosanitaria",
        "aire acondicionado": "aac",
        "sistema contra incendios": "sci",
        "carpintería": "carpinteria",
        "mobiliario": "mobiliario",
        "mampostería": "mamposteria",
        "obra civil": "obra_civil",
        "topografía": "topografia",
        "urbanización": "urbanizacion",
        "cubierta": "cubierta",
        "impermeabilización": "impermeabilizacion",
        "estructura metálica": "estructura_metalica",
        "señalización": "senalizacion",
        "acabados": "acabados",
    }

    field = mapping.get(plantilla)

    if not field:
        return []

    values = data.get(field) or ""

    selected_options = [
        x.strip()
        for x in values.split(",")
        if x.strip()
        and x.strip().lower() != "otros"
    ]

    option_map = PUNTOS_OPCION_MAP.get(field)

    if option_map:
        # El texto oficial de la plantilla, expandido desde cada opción
        # elegida (una opción puede cubrir una o varias líneas) -
        # deduplicado por si dos opciones comparten la misma línea.
        points = []
        seen = set()

        for option in selected_options:
            for line in option_map.get(option.lower(), [option]):
                if line not in seen:
                    seen.add(line)
                    points.append(line)
    else:
        # Todavía no se revisó la plantilla oficial de este rubro -
        # se usa el texto de la opción tal cual, como antes.
        points = selected_options

    points.extend(split_lines(data.get("otros_revision")))

    return points


def build_blocks(data, rubrics):
    """Build replacement blocks for Excel template with data from item and rubrics."""

    code = rubric_code(
        data.get("rubro")
    )

    spec = build_template_points(data)

    programacion = build_programacion(
        data.get(
            "subitems",
            []
        )
    )

    print("SPEC =", spec)
    print("IMMUTABLE =", IMMUTABLE_POINTS)

    blocks = {

        "{{PROGRAMACION}}":
        "\n".join([
            " | ".join([
                r["area"],
                r["inicio"],
                r["fin"],
                r["obs"],
            ])
            for r in programacion
        ]),

        "__PROGRAMACION_ROWS__":
        programacion,

        "{{TRABAJOS_PREVIOS}}":
        split_lines(
            data.get(
                "trabajos_previos"
            )
        ),

        "{{SERVICIOS_BASICOS}}":
        build_services(data),

        "{{PUNTOS_REVISION}}":
        spec + IMMUTABLE_POINTS,
    }

    blocks.update(
        build_multas(data)
    )

    blocks.update(
        build_puntos_generales(data)
    )

    blocks.update(
        build_planos(data)
    )

    return blocks
    

def parse_multi(value):

    return {
        x.strip().lower()
        for x in (value or "").split(",")
        if x.strip()
    }


def build_multas(data):
    """Resolve which multas apply from the MULTAS_COLUMN_ID dropdown selection.

    A selected multa renders with its default amount (from the original
    template); anything not selected renders as "N/A".
    """

    selected_options = parse_multi(data.get("multas_aplicar"))
    print("MULTAS_SELECCIONADAS =", selected_options)

    selected_keys = {
        MULTAS_OPTION_MAP[option]
        for option in selected_options
        if option in MULTAS_OPTION_MAP
    }

    def value_for(key):
        return MULTAS_DEFAULTS[key] if key in selected_keys else "N/A"

    return {
        "{{MULTA_ATRASO}}": value_for("atraso"),
        "{{MULTA_ORDEN}}": value_for("orden"),
        "{{MULTA_SEGURIDAD}}": value_for("seguridad"),
        "{{MULTA_REPORTERIA}}": value_for("reporteria"),
    }


def build_puntos_generales(data):

    selected = parse_multi(
        data.get("puntos_generales")
    )
    print("SELECTED_PUNTOS =", selected)

    return {

        "{{PG_BITACORA}}":
            "SI" if "llevar bitácora diaria" in selected else "NO",

        "{{PG_SEGURIDAD}}":
            "SI" if "encargado de seguridad industrial" in selected else "NO",

        "{{PG_PROTOCOLO}}":
            "SI" if "protocolo de seguridad" in selected else "NO",

        "{{PG_REUNION}}":
            "SI" if "reunión semanal con lider de proyecto" in selected else "NO",

        "{{PG_SUPERVISOR}}":
            "SI" if "arq / ing para supervisar" in selected else "NO",

        "{{PG_ENCARGADO}}":
        "SI"
        if any(
            "encargado técnico de supervisión" in x
            for x in selected
        )
        else "NO",
    }


def build_planos(data):

    selected = parse_multi(
        data.get("planos_entregados")
    )

    return {

        "{{PL_ARQ}}":
            "SI" if "arquitectura" in selected else "NO",

        "{{PL_COTAS}}":
            "SI" if "cotas" in selected else "NO",

        "{{PL_ELEV}}":
            "SI" if "elevaciones y secciones" in selected else "NO",

        "{{PL_HIDRO}}":
            "SI" if "hidrosanitarias" in selected else "NO",

        "{{PL_ELEC}}":
            "SI" if "electricidad" in selected else "NO",

        "{{PL_ACAB}}":
            "SI" if "acabados" in selected else "NO",

        "{{PL_ESTR_PRIN}}":
            "SI" if "estructura principal" in selected else "NO",

        "{{PL_ESTR_SEC}}":
            "SI" if "estructura secundaria" in selected else "NO",

        "{{PL_OBRAS}}":
            "SI" if "obras secundarias" in selected else "NO",
    }


