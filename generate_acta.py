import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from config import (
    ACTA_BOARD_ID,
    ACTA_ENVIAR_GERENTE_COLUMN_ID,
    ACTA_ENVIAR_GERENTE_REVISION_LABEL,
    ACTA_ID_COLUMN_ID,
    ACTA_OUTPUT_DIR,
    ACTA_RECHAZADO_LABEL,
    ACTA_STATUS_COLUMN_ID,
    ACTA_TEMPLATE,
    ACTA_TEMPLATE_REFORMA,
    ACTA_XLSX_COLUMN_ID,
    COTIZACION_FILE_COLUMN_ID,
    LIDER_DOCUMENTACION_COLUMN_ID,
    FIRMA_MONDAY_COLUMN_ID,
    GERENTE_LINK_BASE_URL,
    METODO_FIRMA_MONDAY_LABEL,
    SIGNATURE_COLUMN_ID,
)
from utils.monday_client import (
    change_status,
    create_update,
    download_file,
    generate_acta_id,
    get_file_public_url,
    get_file_public_urls,
    get_item,
    upload_file,
    update_text_column,
)
from semanas import es_solicitud_tardia, parse_fecha
from utils.acta_builder import build_blocks, display_date, item_data, pct
from contratistas import aplicar_contratista, escribir_en_item
from utils.cotizacion_upload import parse_cotizacion_upload, validar_plantilla
from utils.excel_writer import render_excel


def _clean(value):
    return re.sub(r"[^A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ._-]+", "_", str(value or "")).strip("_")


class CotizacionInvalida(Exception):
    """El archivo de "Alcance Cotizacion" no es la plantilla oficial."""


def _parse_pct(value):
    value = (value or "").strip().replace("%", "").replace(",", "")

    try:
        return float(value)
    except ValueError:
        return 0.0


GUATEMALA_TZ = ZoneInfo("America/Guatemala")


def fecha_de_creacion(created_at):
    """Fecha (YYYY-MM-DD, hora de Guatemala) del created_at de Monday."""

    return parse_fecha(created_at).astimezone(GUATEMALA_TZ).strftime("%Y-%m-%d")


def _is_late_submission(now=None):
    """Per the Politica de Aprobacion de Puntos de Acta: requests are
    accepted Monday 7:00am to Wednesday 10:00am (Guatemala time). Outside
    that window the request is queued for the following week's cycle -
    here it only flags it (see firma_gerente.py for the hold itself)."""

    return es_solicitud_tardia(now or datetime.now(GUATEMALA_TZ))


def generate_acta(item_id):
    item = get_item(item_id)
    data = item_data(item)

    board_id = int(data.get("board_id") or ACTA_BOARD_ID)

    # Fecha del acta automatica: si el formulario ya no la pregunta (o quedo
    # vacia), es la fecha en que se creo el item, en hora de Guatemala. Si el
    # Lider la escribio, manda lo que escribio.
    if not data.get("fecha_acta") and item.get("created_at"):
        data["fecha_acta"] = fecha_de_creacion(item["created_at"])

    if not data.get("acta_id"):
        data["acta_id"] = generate_acta_id()
        update_text_column(item_id, board_id, ACTA_ID_COLUMN_ID, data["acta_id"])

    print("ACTA_ID =", data.get("acta_id"))
    print("PUNTOS_GENERALES:", data.get("puntos_generales"))
    print("PLANOS_ENTREGADOS:", data.get("planos_entregados"))
    print("MULTAS_APLICAR =", data.get("multas_aplicar"))

    if _is_late_submission():
        print("SOLICITUD FUERA DE PLAZO (Lunes 7:00am - Miercoles 10:00am)")
        try:
            create_update(
                item_id,
                "Esta solicitud se recibio fuera del horario oficial "
                "(Lunes 7:00am a Miercoles 10:00am) segun la Politica de "
                "Aprobacion de Puntos de Acta. Sera programada para el "
                "siguiente ciclo de revision semanal.",
            )
        except Exception as e:
            print(f"ERROR_LATE_FLAG: {e}")

    change_status(item_id, board_id, ACTA_STATUS_COLUMN_ID, "Procesando")

    try:
        base = Path(__file__).resolve().parent

        rubrics = json.loads((base / "rubros.json").read_text(encoding="utf-8"))

        # Contratista elegido de la Base de Datos: trae empresa, NIT, contacto,
        # telefono, correo y RTU de ahi (apagado si la columna no esta configurada).
        original = data
        data = aplicar_contratista(item_id, data)

        if data is not original:
            escribir_en_item(item_id, board_id, original, data)

        replacements = {
            "{{PROYECTO}}": data["proyecto"].upper(),
            "{{LIDER}}": data.get("lider_proyecto", "").upper(),
            "{{RUBRO}}": data["rubro"].upper(),
            "{{TIPO_CONTRATO}}": data["tipo_contrato"].upper(),
            "{{EMPRESA}}": data["empresa"].upper(),
            "{{CONTACTO}}": data["contacto"].upper(),
            "{{TELEFONO}}": data["telefono"],
            "{{NIT}}": data["nit"],
            "{{GERENTE_PROYECTO}}": data.get("gerente_proyecto", "").upper(),
            "{{NO_COTIZACION}}": data["no_cotizacion"],
            "{{ANTICIPO}}": pct(data["anticipo"]),
            "{{ESTIMACIONES}}": pct(data["estimaciones"]),
            "{{CONTRA_ENTREGA}}": pct(data["contra_entrega"]),
            "{{RETENIDO}}": pct(data["retenido"]),
            "{{NO_CONTRATO}}": data["no_contrato"],
            "{{FECHA_ACTA}}": display_date(data["fecha_acta"]),
        }

        replacements.update(build_blocks(data, rubrics))

        missing = [f for f in ("proyecto", "rubro", "no_contrato", "empresa") if not data.get(f)]

        if missing:
            raise ValueError("Campos obligatorios vacíos: " + ", ".join(missing))

        # Validacion de forma de pago: el formulario ya le pide al Lider que
        # los porcentajes sumen 100%, pero nada lo obligaba - sin esto, un
        # Punto de Acta con montos mal repartidos se generaba y enviaba igual.
        pct_fields = {
            "anticipo": data.get("anticipo"),
            "estimaciones": data.get("estimaciones"),
            "contra_entrega": data.get("contra_entrega"),
            "retenido": data.get("retenido"),
        }
        pct_total = sum(_parse_pct(v) for v in pct_fields.values())

        if abs(pct_total - 100) > 0.5:
            detalle = ", ".join(f"{k}: {_parse_pct(v):g}%" for k, v in pct_fields.items())
            try:
                create_update(
                    item_id,
                    "No se genero el Punto de Acta: los porcentajes de forma de pago no "
                    f"suman 100% (suman {pct_total:g}%). Valores actuales - {detalle}. "
                    "Corrige los porcentajes en el formulario y vuelve a intentar.",
                )
            except Exception as e:
                print(f"ERROR_PCT_FLAG: {e}")
            raise ValueError(f"Los porcentajes de forma de pago suman {pct_total:g}%, no 100%")

        stem = _clean(f"PA-{data['no_contrato']}-{data['rubro']}-{data['proyecto']}")[:140]

        output_directory = Path(ACTA_OUTPUT_DIR)
        output_directory.mkdir(parents=True, exist_ok=True)

        xlsx = str(output_directory / f"{stem}.xlsx")

        cotizacion_rows = []

        try:
            if COTIZACION_FILE_COLUMN_ID:
                # El archivo MAS RECIENTE de la columna: si el Lider corrige
                # subiendo la plantilla correcta sin borrar la equivocada, la
                # nueva es la que cuenta.
                archivos = get_file_public_urls(item, COTIZACION_FILE_COLUMN_ID)

                if archivos:
                    nombre_archivo, cotizacion_url = archivos[-1]
                    suffix = (
                        Path(nombre_archivo).suffix
                        or Path(cotizacion_url.split("?")[0]).suffix
                        or ".xlsx"
                    )
                    cotizacion_path = str(output_directory / f"{stem}_cotizacion{suffix}")
                    download_file(cotizacion_url, cotizacion_path)

                    motivo = validar_plantilla(cotizacion_path, nombre_archivo)

                    if motivo:
                        raise CotizacionInvalida(motivo)

                    cotizacion_rows = parse_cotizacion_upload(cotizacion_path)
        except CotizacionInvalida:
            raise
        except Exception as e:
            print(f"ERROR COTIZACION_UPLOAD: {e}")
            cotizacion_rows = []

        print("COTIZACION_ROWS =", cotizacion_rows)

        replacements["__COTIZACION_ROWS__"] = cotizacion_rows

        # Lista de anexos al pie del documento: lo que el Lider adjunto.
        anexos = []

        try:
            if COTIZACION_FILE_COLUMN_ID:
                cot_files = get_file_public_urls(item, COTIZACION_FILE_COLUMN_ID)

                if cot_files:
                    anexos.append(f"Cotización: {cot_files[-1][0]}")

            if LIDER_DOCUMENTACION_COLUMN_ID:
                for nombre_doc, _url in get_file_public_urls(item, LIDER_DOCUMENTACION_COLUMN_ID):
                    anexos.append(f"Documentación: {nombre_doc}")
        except Exception as e:
            print(f"ERROR ANEXOS: {e}")

        replacements["__ANEXOS__"] = anexos

        signature_path = None

        metodo_firma = (data.get("metodo_firma") or "").strip().lower()

        if metodo_firma == METODO_FIRMA_MONDAY_LABEL.strip().lower() and FIRMA_MONDAY_COLUMN_ID:
            firma_column_id = FIRMA_MONDAY_COLUMN_ID
        else:
            firma_column_id = SIGNATURE_COLUMN_ID

        print(f"METODO_FIRMA = {metodo_firma!r} -> columna {firma_column_id}")

        try:
            signature_url = get_file_public_url(item, firma_column_id)

            if signature_url:
                suffix = Path(signature_url.split("?")[0]).suffix or ".png"
                signature_path = str(output_directory / f"{stem}_firma{suffix}")
                download_file(signature_url, signature_path)
        except Exception as e:
            print(f"ERROR FIRMA: {e}")
            signature_path = None

        replacements["__SIGNATURE_PATH__"] = signature_path

        tipo_plantilla = (data.get("tipo_plantilla") or "").strip().lower()
        template = ACTA_TEMPLATE_REFORMA if tipo_plantilla == "reforma" else ACTA_TEMPLATE

        render_excel(base / template, xlsx, replacements)

        # upload_file() puede devolver "exitoso" (sin errores de GraphQL)
        # y aun asi Monday no dejar el archivo pegado en la columna del
        # lado de ellos - nos paso en produccion: el item llegaba a
        # "Generado" con la columna de archivo vacia, y el Gerente se
        # encontraba con "El item no tiene un acta generada todavia" al
        # intentar firmar. Por eso aqui se vuelve a consultar el item
        # despues de subir para confirmar que el archivo si aparece,
        # con un reintento antes de darse por vencido.
        uploaded_url = None

        for attempt in range(2):
            upload_file(item_id, ACTA_XLSX_COLUMN_ID, xlsx)
            uploaded_url = get_file_public_url(get_item(item_id), ACTA_XLSX_COLUMN_ID)

            if uploaded_url:
                break

            print(f"ACTA: item={item_id} el archivo no aparecio en Monday tras subirlo (intento {attempt + 1})")

        if not uploaded_url:
            raise RuntimeError(
                f"El archivo se subio sin error reportado por Monday, pero no aparece "
                f"en la columna {ACTA_XLSX_COLUMN_ID} despues de reintentar"
            )

        change_status(item_id, board_id, ACTA_STATUS_COLUMN_ID, "Generado")

        # El enlace de firma ya no se manda solo - el Lider debe revisar
        # el documento generado y cambiar "Enviar a Gerente" a "Enviar"
        # cuando este listo (ver acta_routes.py). Aqui solo se deja esa
        # columna en "En Revision" para que quede claro que ya hay algo
        # que revisar.
        if ACTA_ENVIAR_GERENTE_COLUMN_ID:
            change_status(item_id, board_id, ACTA_ENVIAR_GERENTE_COLUMN_ID, ACTA_ENVIAR_GERENTE_REVISION_LABEL)

        return {"xlsx": xlsx, "name": stem}

    except CotizacionInvalida as exc:
        # No es un error del sistema: el Lider subio otro documento en vez de
        # la plantilla. Se rechaza y se le explica que hacer, en el item.
        change_status(item_id, board_id, ACTA_STATUS_COLUMN_ID, ACTA_RECHAZADO_LABEL)

        try:
            enlace = f"{GERENTE_LINK_BASE_URL}/plantilla-alcance-cotizacion"
            create_update(
                item_id,
                "<p>El Alcance de Cotización proporcionado por el Líder de Proyecto no es la "
                "plantilla solicitada en el formulario. "
                f'(<a href="{enlace}">PLANTILLA_ALCANCE_COTIZACION.xlsx</a>)</p>'
                "<p>Se adjunta la plantilla solicitada.</p>"
                "<p>En este caso, se debe volver a llenar el formulario con la plantilla correcta.</p>",
            )
        except Exception as e:
            print(f"ERROR_RECHAZO_COTIZACION: {e}")

        print(f"ACTA: item={item_id} rechazado por cotizacion invalida: {exc}")
        return None
    except Exception:
        try:
            change_status(item_id, board_id, ACTA_STATUS_COLUMN_ID, "Error")
        finally:
            raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("item_id")
    args = parser.parse_args()

    print(generate_acta(args.item_id))
