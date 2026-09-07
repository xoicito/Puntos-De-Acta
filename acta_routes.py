import os, threading
from flask import Blueprint, jsonify, request
from config import ACTA_BOARD_ID, ACTA_TRIGGER_LABEL
from generate_acta import generate_acta

acta_bp=Blueprint("acta_bp",__name__)

def _run(item_id):
    try: generate_acta(item_id)
    except Exception as exc: print(f"[PUNTOS_ACTA] item={item_id} error={exc}",flush=True)

@acta_bp.post("/webhook/puntos-acta")
def puntos_acta_webhook():
    payload=request.get_json(silent=True) or {}
    if "challenge" in payload: return jsonify({"challenge":payload["challenge"]})
    event=payload.get("event",payload)
    board_id=str(event.get("boardId") or event.get("board_id") or "")
    item_id=event.get("pulseId") or event.get("itemId") or event.get("item_id")
    value=event.get("value") or event.get("columnValue") or {}
    label=value.get("label",{}).get("text") if isinstance(value,dict) else ""
    if str(ACTA_BOARD_ID)==board_id and item_id and (not label or label==ACTA_TRIGGER_LABEL):
        threading.Thread(target=_run,args=(str(item_id),),daemon=True).start()
    return jsonify({"ok":True})
