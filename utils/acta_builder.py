from datetime import datetime
from config import COLUMN_ALIASES, SUBITEM_COLUMNS

IMMUTABLE_POINTS = [
    "CAMBIO DE PROVEEDOR: Si el proveedor no reacciona a los requerimientos solicitados previos y a los contratados, se debe cambiar no más de 3 días después de la falta de reacción.",
    "GARANTÍA: Si el proveedor tuvo un trabajo de mala calidad, se deben descontar materiales y otros gastos que se requieran.",
    "RETENCIÓN: 5% del monto total retenido por 3 meses luego de haber recibido con satisfacción los trabajos.",
    "El proveedor se compromete a cumplir con todas las normas del ACUERDO GUBERNATIVO 229-204 Y SUS REFORMAS 33-2016. De no cumplir con las normativas del acuerdo o las internas del proyecto, se podrá dar por terminado el contrato.",
]


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

def parse_multi(value):

    return {
        x.strip().lower()
        for x in (value or "").split(",")
        if x.strip()
    }


def build_puntos_generales(data):

    selected = parse_multi(
        data.get("puntos_generales")
    )

    return {
        "bitacora": (
            "SI"
            if "llevar bitácora diaria" in selected
            else "NO"
        ),
        "seguridad": (
            "SI"
            if "encargado de seguridad industrial" in selected
            else "NO"
        ),
        "protocolo": (
            "SI"
            if "protocolo de seguridad" in selected
            else "NO"
        ),
        "reunion": (
            "SI"
            if "reunión semanal con líder de proyecto" in selected
            else "NO"
        ),
        "supervisor": (
            "SI"
            if "arq / ing para supervisar" in selected
            else "NO"
        ),
        "encargado_tecnico": (
            "SI"
            if "encargado técnico de supervisión (maestro de obras, etc)" in selected
            else "NO"
        ),
    }
    print(
    build_puntos_generales(data)
)


def parse_multi(value):

    return {
        x.strip().lower()
        for x in (value or "").split(",")
        if x.strip()
    }


def build_puntos_generales(data):

    selected = parse_multi(
        data.get("puntos_generales")
    )

    return {
        "bitacora": "SI" if "llevar bitácora diaria" in selected else "NO",
        "seguridad": "SI" if "encargado de seguridad industrial" in selected else "NO",
        "protocolo": "SI" if "protocolo de seguridad" in selected else "NO",
        "reunion": "SI" if "reunión semanal con líder de proyecto" in selected else "NO",
        "supervisor": "SI" if "arq / ing para supervisar" in selected else "NO",
        "encargado_tecnico": "SI" if "encargado técnico de supervisión (maestro de obras, etc)" in selected else "NO",
    }
    

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


def build_blocks(data, rubrics):
    """Build replacement blocks for Excel template with data from item and rubrics."""
    code = rubric_code(
        data.get("rubro")
    )

    spec = (
        rubrics
        .get(code, {})
        .get(
            "puntos_revision",
            []
        )
    )

    programacion = build_programacion(
        data.get(
            "subitems",
            []
        )
    )

    return {

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

        "{{CONDICIONES_ESPECIALES}}":
        split_lines(
            data.get(
                "condiciones_especiales"
            )
        ),
    }
