# Puntos de Acta E4

Archivos listos para integrarse al repositorio existente de Contrato Fast Track E4.

## Instalación
1. Copie todos los archivos y carpetas al nivel de `app.py`.
2. Agregue las dependencias de `requirements.txt` (ya incluidas en el proyecto).
3. Configure en Render las variables de `.env.example`; nunca suba el token real a GitHub.
4. En el board de Monday.com cree dos columnas de tipo **Archivos** para la salida XLSX y PDF. Copie sus IDs en `ACTA_XLSX_COLUMN_ID` y `ACTA_PDF_COLUMN_ID`.
5. Configure el webhook de Monday hacia `/webhook/puntos-acta`.

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

3. Cambie el estado del item a `Generar`

4. El sistema procesará automáticamente y generará dos archivos:
   - Archivo XLSX con los datos del acta
   - Archivo PDF (si LibreOffice está disponible)

5. Los archivos se cargarán automáticamente en las columnas especificadas

## Estructura del proyecto

```
.
├── app.py                          # Aplicación Flask principal
├── acta_routes.py                  # Rutas y webhook de Monday.com
├── generate_acta.py                # Lógica principal de generación
├── config.py                       # Configuración y constantes
├── requirements.txt                # Dependencias Python
├── rubros.json                     # Datos de rubros con puntos de revisión
├── .env.example                    # Plantilla de variables de entorno
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
ACTA_STATUS_COLUMN_ID=estado_10
ACTA_TRIGGER_LABEL=Generar
ACTA_TEMPLATE=templates/100_PUNTO_DE_ACTA_PLANTILLA.xlsx
ACTA_OUTPUT_DIR=/tmp/puntos_acta
PORT=10000
```

## Dependencias

- **Flask**: Framework web para las rutas
- **requests**: Cliente HTTP para llamadas a API de Monday.com
- **openpyxl**: Lectura y escritura de archivos Excel
- **gunicorn**: Servidor WSGI para producción
- **LibreOffice** (opcional): Conversión de Excel a PDF

## Notas técnicas

- `rubros.json` contiene los puntos de revisión específicos para cada rubro (101-117)
- Se agregan automáticamente 4 puntos obligatorios al final de la revisión (CAMBIO DE PROVEEDOR, GARANTÍA, RETENCIÓN, NORMATIVAS)
- La conversión a PDF requiere LibreOffice instalado en el servidor
- Los archivos de salida se generan en el directorio especificado por `ACTA_OUTPUT_DIR`
- El sistema maneja tanto nombres de columnas como IDs del API de Monday.com (para compatibilidad con migraciones)

## Mantenimiento

- Actualizar `rubros.json` si cambian los puntos de revisión
- Ajustar las plantillas Excel según necesidades
- Revisar logs en Render si hay errores en la generación
- Verificar que el webhook de Monday.com esté configurado correctamente

## Licencia

Este proyecto forma parte de Contrato Fast Track E4.
