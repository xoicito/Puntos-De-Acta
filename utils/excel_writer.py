from copy import copy
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.styles import Alignment

BLOCKS={"{{PROGRAMACION}}","{{TRABAJOS_PREVIOS}}","{{SERVICIOS_BASICOS}}","{{PUNTOS_REVISION}}","{{CONDICIONES_ESPECIALES}}"}

def render_excel(template_path, output_path, replacements):
    wb=load_workbook(template_path); found=set()
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if not isinstance(cell.value,str): continue
                original=cell.value
                for token,value in replacements.items():
                    if token in cell.value:
                        cell.value=cell.value.replace(token,str(value or "")); found.add(token)
                        if token in BLOCKS:
                            cell.alignment=copy(cell.alignment); cell.alignment=Alignment(horizontal="left",vertical="top",wrap_text=True)
                            lines=max(1,cell.value.count("\n")+1); ws.row_dimensions[cell.row].height=max(ws.row_dimensions[cell.row].height or 15, min(409, 14*lines))
                if original != cell.value: cell.data_type='s'
    missing=sorted(set(replacements)-found)
    if missing: raise ValueError("Placeholders no encontrados: "+", ".join(missing))
    Path(output_path).parent.mkdir(parents=True,exist_ok=True)
    wb.calculation.fullCalcOnLoad=True; wb.calculation.forceFullCalc=True; wb.calculation.calcMode="auto"
    wb.save(output_path); return output_path
