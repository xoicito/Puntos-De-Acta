from openpyxl import load_workbook
from openpyxl.styles import Alignment


def render_excel(template_path, output_path, replacements):

    wb = load_workbook(template_path)

    for ws in wb.worksheets:

        for row in ws.iter_rows():

            for cell in row:

                if not isinstance(cell.value, str):
                    continue

                for placeholder, value in replacements.items():

                    if placeholder in cell.value:

                        cell.value = cell.value.replace(
                            placeholder,
                            str(value or "")
                        )

                        cell.alignment = Alignment(
                            wrap_text=True,
                            vertical="top",
                        )

    wb.save(output_path)

    return output_path
