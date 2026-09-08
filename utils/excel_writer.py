from openpyxl import load_workbook
from openpyxl.styles import Alignment

PROGRAM_PLACEHOLDER='{{PROGRAMACION}}'

def render_excel(template_path, output_path, replacements):
    wb=load_workbook(template_path)
    rows=replacements.pop('__PROGRAMACION_ROWS__',[])
    for ws in wb.worksheets:
        prog_cell=None
        for row in ws.iter_rows():
            for cell in row:
                if cell.value==PROGRAM_PLACEHOLDER:
                    prog_cell=cell
                if isinstance(cell.value,str):
                    for k,v in replacements.items():
                        if isinstance(v,str) and k in cell.value:
                            cell.value=cell.value.replace(k,v)
                            cell.alignment=Alignment(wrap_text=True,vertical='top')
        if prog_cell:
            r=prog_cell.row
            if rows:
                text='
'.join([f"{x['area']} | {x['inicio']} | {x['fin']} | {x['obs']}" for x in rows])
            else:
                text='Sin programación registrada'
            ws.cell(r, prog_cell.column).value=text
            ws.cell(r, prog_cell.column).alignment=Alignment(wrap_text=True,vertical='top')
            ws.row_dimensions[r].height=max(90,18*(len(rows)+1))
    wb.save(output_path)
    return output_path
