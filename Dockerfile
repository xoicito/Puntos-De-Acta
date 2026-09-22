FROM python:3.12-slim

# libreoffice-calc: headless spreadsheet-to-PDF conversion, used when
# Melissa signs (sign_document.py -> utils/pdf_convert.py). Render's
# native Python buildpack doesn't include this, hence the Dockerfile.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-calc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=10000
EXPOSE 10000

CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:$PORT"]
