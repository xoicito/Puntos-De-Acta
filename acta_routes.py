import threading

from flask import Blueprint, jsonify, request

from config import (
    ACTA_BOARD_ID,
    ACTA_ENVIAR_GERENTE_COLUMN_ID,
    ACTA_ENVIAR_GERENTE_ENVIANDO_LABEL,
    ACTA_ENVIAR_GERENTE_TRIGGER_LABEL,
    ACTA_STATUS_COLUMN_ID,
    ACTA_TRIGGER_LABEL,
    FIRMA_BOARD_ID,
    FIRMA_ESTADO_COLUMN_ID,
    FIRMA_TRIGGER_LABELS,
    INTERNAL_TASK_SECRET,
)
from control_facturas import reporte_etiquetas
from escalacion import check_escalaciones
from firma_gerente import start_gerente_signing
from firmas_orden import mover_a_pasados, movimientos_recientes, ordenar_firmas
from generate_acta import generate_acta
from retencion import liberar_retenidos
from semanas import agrupar_semana_actual, asignar_grupo_semanal
from sign_document import sign_document
from utils.monday_client import change_status


acta_bp = Blueprint("acta_bp", __name__)


def _run(item_id):
    try:
        generate_acta(item_id)
    except Exception as exc:
        print(
            f"[PUNTOS_ACTA] item={item_id} error={exc}",
            flush=True,
        )


def _run_nuevo(item_id, board_id):
    """Item recien creado por el formulario: primero se acomoda en el grupo de
    su semana (miercoles 10:01 a miercoles 10:00) y luego se genera. Si mover
    de grupo falla, igual se genera - lo importante es el documento."""

    try:
        asignar_grupo_semanal(item_id, board_id)
    except Exception as exc:
        print(f"[PUNTOS_ACTA] item={item_id} no se pudo asignar el grupo semanal: {exc}", flush=True)

    _run(item_id)


def _run_enviar_gerente(item_id, board_id):
    try:
        start_gerente_signing(item_id, board_id)
        if ACTA_ENVIAR_GERENTE_COLUMN_ID:
            change_status(item_id, board_id, ACTA_ENVIAR_GERENTE_COLUMN_ID, ACTA_ENVIAR_GERENTE_ENVIANDO_LABEL)
    except Exception as exc:
        print(
            f"[PUNTOS_ACTA] item={item_id} error al enviar a gerente: {exc}",
            flush=True,
        )


def _run_signature(item_id, tipo_contrato_mensaje):
    try:
        sign_document(item_id, tipo_contrato_mensaje)
    except Exception as exc:
        print(
            f"[FIRMA_MELISSA] item={item_id} error={exc}",
            flush=True,
        )


@acta_bp.post("/webhook/puntos-acta")
def puntos_acta_webhook():

    payload = request.get_json(silent=True) or {}

    if "challenge" in payload:
        return jsonify({"challenge": payload["challenge"]})

    event = payload.get("event", payload)

    board_id = str(
        event.get("boardId")
        or event.get("board_id")
        or ""
    )

    item_id = (
        event.get("pulseId")
        or event.get("itemId")
        or event.get("item_id")
    )

    column_id = (
        event.get("columnId")
        or event.get("column_id")
        or ""
    )

    value = (
        event.get("value")
        or event.get("columnValue")
        or {}
    )

    label = ""

    if isinstance(value, dict):
        label = (
            value.get("label", {})
            .get("text", "")
            .strip()
        )

    event_type = event.get("type") or ""

    print(
        f"[PUNTOS_ACTA] board={board_id} item={item_id} column={column_id} label='{label}' type='{event_type}'",
        flush=True,
    )

    # Generacion automatica al crear el item (Lider llena el form -> Monday
    # crea el item -> se genera solo, sin que nadie tenga que tocar
    # "Estado"). El automation de Monday que manda este webhook es del
    # tipo "when an item is created" - el payload que manda no trae
    # columnId/value (no es un cambio de columna), solo el tipo de evento,
    # por eso es una condicion aparte de la de abajo. "create_pulse" es el
    # valor que Monday usa para ese tipo de automation; si algun dia
    # cambia, el log de arriba (event_type) lo va a mostrar para poder
    # corregirlo.
    if (
        str(ACTA_BOARD_ID) == board_id
        and item_id
        and event_type in ("create_pulse", "create_item")
    ):
        threading.Thread(
            target=_run_nuevo,
            args=(str(item_id), ACTA_BOARD_ID),
            daemon=True,
        ).start()

    # Se deja tambien el disparador manual por "Estado" -> "Generar" - util
    # para volver a generar un item a mano si algo fallo (ver generate_acta.py,
    # ahora verifica que el archivo si haya quedado subido en Monday).
    elif (
        str(ACTA_BOARD_ID) == board_id
        and item_id
        and (not column_id or column_id == ACTA_STATUS_COLUMN_ID)
        and label == ACTA_TRIGGER_LABEL
    ):
        threading.Thread(
            target=_run,
            args=(str(item_id),),
            daemon=True,
        ).start()

    elif (
        str(ACTA_BOARD_ID) == board_id
        and item_id
        and column_id == ACTA_ENVIAR_GERENTE_COLUMN_ID
        and label == ACTA_ENVIAR_GERENTE_TRIGGER_LABEL
    ):
        threading.Thread(
            target=_run_enviar_gerente,
            args=(str(item_id), ACTA_BOARD_ID),
            daemon=True,
        ).start()

    return jsonify({"ok": True})


@acta_bp.post("/webhook/firma-melissa")
def firma_melissa_webhook():

    payload = request.get_json(silent=True) or {}

    if "challenge" in payload:
        return jsonify({"challenge": payload["challenge"]})

    event = payload.get("event", payload)

    board_id = str(
        event.get("boardId")
        or event.get("board_id")
        or ""
    )

    item_id = (
        event.get("pulseId")
        or event.get("itemId")
        or event.get("item_id")
    )

    column_id = (
        event.get("columnId")
        or event.get("column_id")
        or ""
    )

    value = (
        event.get("value")
        or event.get("columnValue")
        or {}
    )

    label = ""

    if isinstance(value, dict):
        label = (
            value.get("label", {})
            .get("text", "")
            .strip()
        )

    print(
        f"[FIRMA_MELISSA] board={board_id} item={item_id} column={column_id} label='{label}'",
        flush=True,
    )

    if (
        str(FIRMA_BOARD_ID) == board_id
        and item_id
        and (not column_id or column_id == FIRMA_ESTADO_COLUMN_ID)
        and label in FIRMA_TRIGGER_LABELS
    ):
        threading.Thread(
            target=_run_signature,
            args=(str(item_id), FIRMA_TRIGGER_LABELS[label]),
            daemon=True,
        ).start()

    return jsonify({"ok": True})


@acta_bp.post("/internal/check-escalaciones")
def check_escalaciones_route():
    """Llamado una vez al dia por un cron externo (no una automatizacion de
    Monday - esto es un chequeo por tiempo, no por evento). Protegido por un
    secreto compartido en vez de dejarlo abierto, ya que dispara updates
    visibles en Monday."""

    secret = request.headers.get("X-Internal-Secret", "")

    if not INTERNAL_TASK_SECRET or secret != INTERNAL_TASK_SECRET:
        return jsonify({"error": "unauthorized"}), 401

    try:
        escalated = check_escalaciones()
    except Exception as exc:
        print(f"ESCALACION: error en el chequeo: {exc}", flush=True)
        return jsonify({"ok": False, "error": str(exc)}), 500

    # Mismo cron diario: libera a Procurement los Puntos de Acta que
    # quedaron "En espera" por entrar fuera de horario.
    try:
        liberados = liberar_retenidos()
    except Exception as exc:
        print(f"RETENCION: error al liberar: {exc}", flush=True)
        return jsonify({"ok": False, "escalated": escalated, "error": str(exc)}), 500

    # Y se acomodan por semana los items del board que hayan quedado fuera de
    # su grupo (red de seguridad del acomodo automatico al crearlos).
    try:
        agrupados = agrupar_semana_actual(ACTA_BOARD_ID)
    except Exception as exc:
        print(f"SEMANAS: error al agrupar: {exc}", flush=True)
        agrupados = None

    return jsonify({"ok": True, "escalated": escalated, "liberados": liberados, "agrupados": agrupados})


@acta_bp.get("/internal/etiquetas-facturas")
def etiquetas_facturas_route():
    """Lista las etiquetas de DIVISION y PROYECTO en Control de Facturas y
    marca las que parecen duplicadas (mismo texto salvo mayusculas/tildes, o
    una es el inicio de la otra). Solo lectura, mismo secreto que arriba."""

    secret = request.headers.get("X-Internal-Secret", "")

    if not INTERNAL_TASK_SECRET or secret != INTERNAL_TASK_SECRET:
        return jsonify({"error": "unauthorized"}), 401

    try:
        return jsonify(reporte_etiquetas())
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@acta_bp.post("/internal/ordenar-firmas")
def ordenar_firmas_route():
    """Cron externo, domingo por la noche: pasa los Puntos de Acta ya
    firmados / rechazados en el board de Melissa a sus grupos. Mismo secreto
    que los demas endpoints internos."""

    secret = request.headers.get("X-Internal-Secret", "")

    if not INTERNAL_TASK_SECRET or secret != INTERNAL_TASK_SECRET:
        return jsonify({"error": "unauthorized"}), 401

    try:
        return jsonify({"ok": True, **ordenar_firmas()})
    except Exception as exc:
        print(f"ORDEN_FIRMAS: error: {exc}", flush=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@acta_bp.get("/internal/movimientos-firmas")
def movimientos_firmas_route():
    """Solo lectura: movimientos entre grupos de las ultimas horas en el board
    de Melissa (?minutos=240)."""

    if not INTERNAL_TASK_SECRET or request.headers.get("X-Internal-Secret", "") != INTERNAL_TASK_SECRET:
        return jsonify({"error": "unauthorized"}), 401

    try:
        return jsonify(movimientos_recientes(int(request.args.get("minutos", 240))))
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@acta_bp.post("/internal/devolver-a-pasados")
def devolver_a_pasados_route():
    """Devuelve al grupo PASADOS los items cuyos ids vienen en el JSON
    {"item_ids": [...]}."""

    if not INTERNAL_TASK_SECRET or request.headers.get("X-Internal-Secret", "") != INTERNAL_TASK_SECRET:
        return jsonify({"error": "unauthorized"}), 401

    ids = (request.get_json(silent=True) or {}).get("item_ids") or []

    try:
        return jsonify({"ok": True, "movidos": mover_a_pasados([str(i) for i in ids])})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@acta_bp.post("/internal/agrupar-semanas")
def agrupar_semanas_route():
    """Acomoda por semana, en segundo plano, los items de la semana en curso
    del board de formularios (mismo secreto que los demas endpoints)."""

    if not INTERNAL_TASK_SECRET or request.headers.get("X-Internal-Secret", "") != INTERNAL_TASK_SECRET:
        return jsonify({"error": "unauthorized"}), 401

    threading.Thread(target=agrupar_semana_actual, args=(ACTA_BOARD_ID,), daemon=True).start()

    return jsonify({"ok": True, "estado": "en proceso, revisa el board en un minuto"})


@acta_bp.get("/internal/directorio")
def directorio_diagnostico():
    """Diagnostico solo de lectura del directorio de personas (mismo secreto que
    los demas endpoints internos): cuantas filas lee el servidor, cuantas traen
    correo y, con ?correo=..., que ve del correo buscado. No muestra correos completos."""

    if not INTERNAL_TASK_SECRET or request.headers.get("X-Internal-Secret", "") != INTERNAL_TASK_SECRET:
        return jsonify({"error": "unauthorized"}), 401

    import directorio

    if not directorio.activo():
        return jsonify({"activo": False, "motivo": "Faltan variables DIRECTORIO_* en el servidor (board, correo o rol)."})

    try:
        filas = directorio.personas(forzar=True)
    except Exception as exc:
        return jsonify({"activo": True, "error": f"No se pudo leer el board: {exc}"}), 502

    def mascara(correo):
        usuario, _, dominio = (correo or "").partition("@")

        return (usuario[:2] + "***@" + dominio) if correo else ""

    buscado = (request.args.get("correo") or "").strip().lower()
    persona = next((p for p in filas if buscado and p["correo"] == buscado), None)

    return jsonify({
        "activo": True,
        "board_id": directorio.DIRECTORIO_BOARD_ID,
        "filas_leidas": len(filas),
        "con_correo": sum(1 for p in filas if p["correo"]),
        "con_rol": sum(1 for p in filas if p["roles"]),
        "estados": {e: sum(1 for p in filas if p["acceso"] == e) for e in ("aprobado", "pendiente", "rechazado")},
        "muestra": [{"nombre": p["nombre"], "correo": mascara(p["correo"]), "roles": sorted(p["roles"]), "acceso": p["acceso"]} for p in filas[:5]],
        "correo_buscado": ({"encontrado": True, "nombre": persona["nombre"], "roles": sorted(persona["roles"]), "acceso": persona["acceso"]}
                           if persona else {"encontrado": False}) if buscado else None,
        "ayuda": ("0 filas: el servidor no ve el board (probablemente privado para la cuenta del token de Render) o el ID del board esta mal."
                  if not filas else "con_correo = 0: el ID de la columna Correo en Render no coincide." if not any(p["correo"] for p in filas) else ""),
    })
