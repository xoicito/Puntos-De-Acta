# Puntos de Acta E4

Archivos listos para integrarse al repositorio existente de Contrato Fast Track E4.

## Instalación
1. Copie todos los archivos y carpetas al nivel de `app.py`.
2. Agregue las dependencias de `requirements.txt` (ya incluidas en el proyecto).
3. Configure en Render las variables de `.env.example`; nunca suba el token real a GitHub.
4. En el board de Monday.com cree dos columnas de tipo **Archivos** para la salida XLSX y PDF. Copie sus IDs en `ACTA_XLSX_COLUMN_ID` y `ACTA_PDF_COLUMN_ID`.
5. Configure el webhook de Monday hacia `/webhook/puntos-acta` (dispara cuando `ACTA_STATUS_COLUMN_ID` cambia a `ACTA_TRIGGER_LABEL`).
6. Configure un segundo webhook de Monday, en el board de Aprobación (`FIRMA_BOARD_ID`), hacia `/webhook/firma-melissa` (dispara cuando `FIRMA_ESTADO_COLUMN_ID` cambia a `FIRMA_TRIGGER_LABEL`).

## Flujo de uso
1. Cree un item en el board con los campos requeridos:
   - `Proyecto`
   - `Rubro`
   - `Número de Contrato`
   - `Empresa`

2. Agregue subitems con información de programación:
   - Campo `nombre`: Área de trabajo
   - Campo `fecha0`: Fecha de inicio
   - Campo `fecha__1`: Fecha de fin
   - Campo `texto`: Observaciones

3. (Opcional) Elija el método de firma (`METODO_FIRMA_COLUMN_ID`): subir un PNG a la columna "Archivo" (`SIGNATURE_COLUMN_ID`) o firmar directamente con la experiencia de firma de Monday, columna "Firma" (`FIRMA_MONDAY_COLUMN_ID`). Cualquiera de las dos se insertará en el acta ajustada al recuadro correspondiente sin deformarse.

4. Cambie el estado del item a `Generar`

5. El sistema procesará automáticamente:
   - Genera un `ID de Punto de Acta` único (columna `ACTA_ID_COLUMN_ID`) si el item todavía no tiene uno.
   - Busca en el board de Cotización (`COTIZACION_BOARD_ID`) los items cuyo `Name` sea igual a ese ID y los inserta como filas en "Alcance de Cotización del Proveedor". Para que un renglón de cotización aparezca en el acta, su `Name` debe copiarse exactamente igual al `ID de Punto de Acta` generado.
   - Genera el archivo XLSX con los datos del acta
   - Genera el archivo PDF (si LibreOffice está disponible)

6. Los archivos se cargarán automáticamente en las columnas especificadas

## Firma de aprobación (Arq. Melissa Alvarenga)

Este es un flujo independiente, en un board distinto (`FIRMA_BOARD_ID`), que no depende del flujo de generación anterior:

1. Alguien sube el Excel editable del acta a la columna **PA EDITABLE** (`FIRMA_PA_EDITABLE_COLUMN_ID`) de un item en el board de Aprobación.
2. Melissa cambia **ESTADO DE APROBACIÓN** (`FIRMA_ESTADO_COLUMN_ID`) a `FIRMADO`.
3. El sistema descarga el archivo de PA EDITABLE, inserta su firma (`MELISSA_SIGNATURE_PATH`) sin deformarla, y sube el resultado a **Dup. of PA FIRMADO PRC** (`FIRMA_PA_FIRMADO_COLUMN_ID`) del mismo item.
   - La ubicación de la firma se busca primero como un placeholder de texto (`FIRMA_PLACEHOLDER`, por defecto `{{FIRMA_MELISSA}}`) en cualquier celda de la plantilla; si esa celda es parte de un rango combinado, se usa todo el rango. Esto permite que distintas variantes de plantilla coloquen la firma donde necesiten con solo incluir ese texto.
   - Si la plantilla no tiene el placeholder, se usa como respaldo el recuadro fijo L128:M131.

Todo ocurre dentro del mismo item del board de Aprobación; no requiere relacionarlo con el item del board principal.

## Estructura del proyecto

```
.
├── app.py                          # Aplicación Flask principal
├── acta_routes.py                  # Rutas y webhooks de Monday.com
├── generate_acta.py                # Lógica principal de generación
├── sign_document.py                # Flujo de firma de aprobación (Melissa Alvarenga)
├── config.py                       # Configuración y constantes
├── requirements.txt                # Dependencias Python
├── rubros.json                     # Datos de rubros con puntos de revisión
├── .env.example                    # Plantilla de variables de entorno
├── assets/                         # Imágenes fijas (firma de aprobación)
│   └── firma_melissa.jpg
├── templates/                      # Carpeta para plantillas Excel
│   └── 100_PUNTO_DE_ACTA_PLANTILLA.xlsx
└── utils/
    ├── acta_builder.py            # Construcción de bloques de datos
    ├── excel_writer.py            # Escritura en archivos Excel
    ├── monday_client.py           # Cliente para API de Monday.com
    └── pdf_converter.py           # Conversión de Excel a PDF
```

## Configuración requerida

### Variables de entorno (.env)
```
MONDAY_TOKEN=<tu_token_api_monday>
MONDAY_API_VERSION=2026-01
ACTA_BOARD_ID=<id_del_board>
ACTA_XLSX_COLUMN_ID=<id_columna_xlsx>
ACTA_PDF_COLUMN_ID=<id_columna_pdf>
ACTA_ID_COLUMN_ID=text_mm736ka4
SIGNATURE_COLUMN_ID=file80ymdmtg
METODO_FIRMA_COLUMN_ID=<id_columna_metodo_firma>
FIRMA_MONDAY_COLUMN_ID=signature9vmootoj
ACTA_STATUS_COLUMN_ID=estado_10
ACTA_TRIGGER_LABEL=Generar
ACTA_TEMPLATE=templates/100_PUNTO_DE_ACTA_PLANTILLA.xlsx
ACTA_OUTPUT_DIR=/tmp/puntos_acta
FIRMA_BOARD_ID=18419366411
FIRMA_ESTADO_COLUMN_ID=color_mm4t50
FIRMA_TRIGGER_LABEL=FIRMADO
FIRMA_PA_EDITABLE_COLUMN_ID=file_mm4vcga3
FIRMA_PA_FIRMADO_COLUMN_ID=file_mm7936qy
MELISSA_SIGNATURE_PATH=assets/firma_melissa.jpg
PORT=10000
```

## Dependencias

- **Flask**: Framework web para las rutas
- **requests**: Cliente HTTP para llamadas a API de Monday.com
- **openpyxl**: Lectura y escritura de archivos Excel
- **Pillow**: Requerido por openpyxl para preservar imágenes (logos, firma) al leer/escribir el Excel
- **gunicorn**: Servidor WSGI para producción
- **LibreOffice** (opcional): Conversión de Excel a PDF

## Notas técnicas

- `rubros.json` contiene los puntos de revisión específicos para cada rubro (101-117)
- Se agregan automáticamente 4 puntos obligatorios al final de la revisión (CAMBIO DE PROVEEDOR, GARANTÍA, RETENCIÓN, NORMATIVAS)
- La conversión a PDF requiere LibreOffice instalado en el servidor
- Los archivos de salida se generan en el directorio especificado por `ACTA_OUTPUT_DIR`
- El sistema maneja tanto nombres de columnas como IDs del API de Monday.com (para compatibilidad con migraciones)
- La sección "Condiciones Especiales" fue retirada del flujo (ya no se llena) y sus filas quedan ocultas en la plantilla; no se eliminaron físicamente para no romper las referencias de fila del resto del template

## Mantenimiento

- Actualizar `rubros.json` si cambian los puntos de revisión
- Ajustar las plantillas Excel según necesidades
- Revisar logs en Render si hay errores en la generación
- Verificar que el webhook de Monday.com esté configurado correctamente

## Licencia

Este proyecto forma parte de Contrato Fast Track E4.
