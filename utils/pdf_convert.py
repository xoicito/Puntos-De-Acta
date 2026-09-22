import subprocess
from pathlib import Path


def convert_to_pdf(xlsx_path, output_dir, timeout=120):
    """Convert an xlsx file to PDF using headless LibreOffice.

    Requires the "libreoffice" (or libreoffice-calc) binary on PATH -
    installed via the Dockerfile, since Render's native Python buildpack
    doesn't include it. Returns the path to the resulting PDF.
    """

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [
            "libreoffice",
            "--headless",
            "--norestore",
            "--convert-to", "pdf",
            "--outdir", str(output_dir),
            str(xlsx_path),
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"LibreOffice fallo convirtiendo {xlsx_path} a PDF: "
            f"{result.stderr or result.stdout}"
        )

    pdf_path = output_dir / (Path(xlsx_path).stem + ".pdf")

    if not pdf_path.exists():
        raise RuntimeError(f"LibreOffice no genero el PDF esperado: {pdf_path}")

    return str(pdf_path)
