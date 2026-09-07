from datetime import datetime
from config import COLUMN_ALIASES, SUBITEM_COLUMNS

IMMUTABLE_POINTS=[
"CAMBIO DE PROVEEDOR: Si el proveedor no reacciona a los requerimientos solicitados previos y a los contratados, se debe cambiar no más de 3 días después de la falta de reacción.",
"GARANTÍA: Si el proveedor tuvo un trabajo de mala calidad, se deben descontar materiales y otros gastos que se requieran.",
"RETENCIÓN: 5% del monto total retenido por 3 meses luego de haber recibido con satisfacción los trabajos.",
"El proveedor se compromete a cumplir con todas las normas del ACUERDO GUBERNATIVO 229-204 Y SUS REFORMAS 33-2016. De no cumplir con las normativas del acuerdo o las internas del proyecto, se procederá a aplicar una multa económica según la falta cometida.",
]

def _values(item): return {c["id"]: (c.get("text") or "").strip() for c in item.get("column_values",[])}
def _pick(values,key):
    for cid in COLUMN_ALIASES[key]:
        if values.get(cid): return values[cid]
    return ""
def item_data(item):
    v=_values(item); data={k:_pick(v,k) for k in COLUMN_ALIASES}
    data["item_id"]=str(item["id"]); data["item_name"]=item.get("name","")
    data["board_id"]=str(item.get("board",{}).get("id", ""))
    data["subitems"]=item.get("subitems",[])
    return data

def split_lines(text): return [" ".join(x.split()) for x in (text or "").splitlines() if x.strip()]
def numbered(lines): return "\n".join(f"{i}. {x}" for i,x in enumerate(lines,1))
def pct(value):
    value=(value or "").strip(); return value if not value or value.endswith("%") else value+"%"
def display_date(value):
    if not value: return ""
    for fmt in ("%Y-%m-%d","%m/%d/%Y","%d/%m/%Y"):
        try: return datetime.strptime(value,fmt).strftime("%d/%m/%Y")
        except ValueError: pass
    return value

def rubric_code(rubro):
    import re
    m=re.search(r"\b(1\d{2})\b",rubro or ""); return m.group(1) if m else "100"
def build_programacion(subitems):
    rows=[]
    for s in subitems:
        v={c["id"]:(c.get("text") or "").strip() for c in s.get("column_values",[])}
        area=(s.get("name") or "").strip(); ini=display_date(v.get(SUBITEM_COLUMNS["fecha_inicio"],"")); fin=display_date(v.get(SUBITEM_COLUMNS["fecha_fin"],"")); obs=v.get(SUBITEM_COLUMNS["observaciones"],"")
        dias=""
        try: dias=str((datetime.strptime(fin,"%d/%m/%Y")-datetime.strptime(ini,"%d/%m/%Y")).days+1)
        except Exception: pass
        if any((area,ini,fin,obs)): rows.append(" | ".join([area,ini,fin,dias,obs]))
    return "ÁREA | INICIO | TERMINA | DÍAS | OBSERVACIONES" + (("\n"+"\n".join(rows)) if rows else "\nSin programación registrada")
def build_services(data):
    values=[x.strip() for x in (data.get("servicios_basicos") or "").replace(";",",").split(",") if x.strip()]
    other=data.get("otro_servicio_basico","").strip()
    if other and other.lower() not in {x.lower() for x in values}: values.append(other)
    return numbered(values) if values else "No aplica"
def build_blocks(data,rubrics):
    code=rubric_code(data.get("rubro")); spec=rubrics.get(code,{}).get("puntos_revision",[])
    return {
      "{{PROGRAMACION}}": build_programacion(data.get("subitems",[])),
      "{{TRABAJOS_PREVIOS}}": numbered(split_lines(data.get("trabajos_previos"))) or "No aplica",
      "{{SERVICIOS_BASICOS}}": build_services(data),
      "{{PUNTOS_REVISION}}": numbered(spec+IMMUTABLE_POINTS),
      "{{CONDICIONES_ESPECIALES}}": ("CONDICIONES ESPECIALES\n"+numbered(split_lines(data.get("condiciones_especiales")))) if split_lines(data.get("condiciones_especiales")) else "",
    }
