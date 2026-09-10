import shutil
import subprocess
from pathlib import Path


def convert_excel_to_pdf(xlsx_path, output_dir):
    """Convert an Excel file to PDF using LibreOffice."""
    binary = shutil.which("libreoffice") or shutil.which("soffice")

    if not binary:
        raise RuntimeError(
            "LibreOffice no está instalado; agréguelo al entorno de Render o desactive la carga PDF"
        )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            binary,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir),
            str(xlsx_path)
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=180
    )

    pdf = output_dir / (Path(xlsx_path).stem + ".pdf")

    if not pdf.exists():
        raise RuntimeError("LibreOffice no generó el PDF")

    return str(pdf)
