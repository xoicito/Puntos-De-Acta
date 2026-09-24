import threading

from flask import Blueprint, jsonify, request

from config import (
    ACTA_BOARD_ID,
    ACTA_TRIGGER_LABEL,
    FIRMA_BOARD_ID,
    FIRMA_ESTADO_COLUMN_ID,
    FIRMA_TRIGGER_LABELS,
)
from generate_acta import generate_acta
from sign_document import sign_document


acta_bp = Blueprint("acta_bp", __name__)


def _run(item_id):
    try:
        generate_acta(item_id)
    except Exception as exc:
        print(
            f"[PUNTOS_ACTA] item={item_id} error={exc}",
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
        f"[PUNTOS_ACTA] board={board_id} item={item_id} label='{label}'",
        flush=True,
    )

    if (
        str(ACTA_BOARD_ID) == board_id
        and item_id
        and label == ACTA_TRIGGER_LABEL
    ):
        threading.Thread(
            target=_run,
            args=(str(item_id),),
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
