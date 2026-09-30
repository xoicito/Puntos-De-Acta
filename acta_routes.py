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
)
from firma_gerente import start_gerente_signing
from generate_acta import generate_acta
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
            target=_run,
            args=(str(item_id),),
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
