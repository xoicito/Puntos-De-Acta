# Puntos de Acta E4

Archivos listos para integrarse al repositorio existente de Contrato Fast Track E4.

## Instalación
1. Copie todos los archivos y carpetas al nivel de `app.py`.
2. Agregue las dependencias de `requirements-actas.txt` a `requirements.txt`.
3. Aplique las dos líneas de `app_integration.txt` en `app.py`.
4. En el board actual cree dos columnas de tipo **Archivos** para la salida XLSX y PDF. Copie sus IDs en `ACTA_XLSX_COLUMN_ID` y `ACTA_PDF_COLUMN_ID`.
5. Configure en Render las variables de `.env.example`; nunca suba el token real a GitHub.
6. Configure el webhook de Monday hacia `/webhook/puntos-acta`.

## Prueba mínima
- Cree un item con `Proyecto`, `Rubro`, `Número de Contrato` y `Empresa`.
- Agregue un subitem: el nombre es Área; `fecha0` es inicio; `fecha__1` es fin; `texto` son observaciones.
- Cambie el estado a `Generar`.
- Espere `Generado` y confirme los dos archivos de salida.

## Notas
- `rubros.json` se generó desde las plantillas 101 a 117.
- Los cuatro puntos obligatorios se agregan siempre al final de la revisión.
- La tabla de alcances se conserva vacía en V1 porque cada proveedor entrega una cotización con formato distinto.
- La conversión a PDF requiere LibreOffice en el servicio. Si Render no lo incluye, use una imagen Docker que lo instale.
