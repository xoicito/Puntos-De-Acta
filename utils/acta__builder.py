from config import COLUMN_ALIASES, SUBITEM_COLUMNS

def _values(item):
    return {c.get('id'): (c.get('text') or '').strip() for c in item.get('column_values', [])}

def _pick(values, key):
    for cid in COLUMN_ALIASES.get(key, []):
        if values.get(cid):
            return values[cid]
    return ''

def item_data(item):
    values = _values(item)
    data = {k: _pick(values, k) for k in COLUMN_ALIASES}
    data['subitems'] = item.get('subitems', [])
    data['board_id'] = str(item.get('board', {}).get('id', ''))
    return data

def split_lines(text):
    return [x.strip() for x in (text or '').replace(';', '
').splitlines() if x.strip()]

def numbered(lines):
    clean=[]
    for x in lines:
        if x[:3].count('.'):
            x=x.split('.',1)[1].strip()
        clean.append(x)
    return '
'.join(f'{i}. {v}' for i,v in enumerate(clean,1))

def pct(v):
    v=(v or '').strip()
    return v if not v or v.endswith('%') else f'{v}%'

def display_date(v):
    return v or ''

def build_programacion_rows(subitems):
    rows=[]
    for s in subitems:
        vals={c.get('id'):(c.get('text') or '').strip() for c in s.get('column_values',[])}
        rows.append({
            'area':(s.get('name') or '').strip(),
            'inicio':vals.get('fecha0',''),
            'fin':vals.get('fecha__1',''),
            'obs':vals.get('texto','')
        })
    return [r for r in rows if any(r.values())]

def build_blocks(data,rubrics):
    return {
      '{{TRABAJOS_PREVIOS}}': numbered(split_lines(data.get('trabajos_previos'))),
      '{{SERVICIOS_BASICOS}}': numbered(split_lines(data.get('servicios_basicos'))),
      '{{PUNTOS_REVISION}}':'',
      '{{CONDICIONES_ESPECIALES}}': numbered(split_lines(data.get('condiciones_especiales'))),
      '__PROGRAMACION_ROWS__': build_programacion_rows(data.get('subitems',[]))
    }
