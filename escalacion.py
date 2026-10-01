from datetime import datetime, timezone

from config import (
    ACTA_BOARD_ID,
    ACTA_ESCALAMIENTO_1_LABEL,
    ACTA_ESCALAMIENTO_2_LABEL,
    ACTA_ESCALAMIENTO_3_LABEL,
    ACTA_ESCALAMIENTO_COLUMN_ID,
    GERENTE_FIRMA_ESTADO_COLUMN_ID,
    GERENTE_FIRMA_ESTADO_FIRMADO,
)
from utils.monday_client import change_status, create_update, list_board_items

# (dias minimos, etiqueta, rango, mensaje) - ordenado de mayor a menor a
# proposito: si el chequeo diario se salta varios dias (o nunca corrio),
# un item de 25 dias debe saltar directo a "3 Semanas", no mandar los 3
# mensajes de golpe.
THRESHOLDS = [
    (21, ACTA_ESCALAMIENTO_3_LABEL, 3,
     "Este Punto de Acta lleva 3 semanas sin que el Gerente de Proyecto lo firme. Segun la "
     "Politica de Aprobacion de Puntos de Acta, Procurement debe proceder con la elaboracion "
     "de la documentacion necesaria y el caso sera presentado en Comite."),
    (14, ACTA_ESCALAMIENTO_2_LABEL, 2,
     "Este Punto de Acta lleva 2 semanas sin que el Gerente de Proyecto lo firme. Segun la "
     "Politica de Aprobacion de Puntos de Acta, corresponde una llamada de atencion escrita "
     "al Lider de Proyecto y al Gerente de Proyecto."),
    (7, ACTA_ESCALAMIENTO_1_LABEL, 1,
     "Este Punto de Acta lleva 1 semana sin que el Gerente de Proyecto lo firme. Segun la "
     "Politica de Aprobacion de Puntos de Acta, corresponde una llamada de atencion verbal "
     "al Lider de Proyecto."),
]


def _level_rank(label):
    return {
        ACTA_ESCALAMIENTO_1_LABEL: 1,
        ACTA_ESCALAMIENTO_2_LABEL: 2,
        ACTA_ESCALAMIENTO_3_LABEL: 3,
    }.get(label, 0)


def check_escalaciones():
    """Corre una vez al dia (ver /internal/check-escalaciones): revisa todo
    ACTA_BOARD_ID y publica un update la primera vez que un item cruza 1, 2
    o 3 semanas desde su creacion sin que el Gerente lo haya firmado todavia.
    El nivel ya avisado queda guardado en ACTA_ESCALAMIENTO_COLUMN_ID para
    nunca repetir el mismo aviso."""

    if not ACTA_ESCALAMIENTO_COLUMN_ID:
        print("ESCALACION: ACTA_ESCALAMIENTO_COLUMN_ID no configurado, se omite")
        return 0

    now = datetime.now(timezone.utc)
    column_ids = [GERENTE_FIRMA_ESTADO_COLUMN_ID, ACTA_ESCALAMIENTO_COLUMN_ID]

    items = list_board_items(ACTA_BOARD_ID, column_ids)
    escalated = 0

    for item in items:
        if item["columns"].get(GERENTE_FIRMA_ESTADO_COLUMN_ID) == GERENTE_FIRMA_ESTADO_FIRMADO:
            continue

        created = item.get("created_at")

        if not created:
            continue

        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        days = (now - created_dt).days

        current_rank = _level_rank(item["columns"].get(ACTA_ESCALAMIENTO_COLUMN_ID))

        for threshold_days, label, rank, message in THRESHOLDS:
            if days >= threshold_days and rank > current_rank:
                change_status(item["id"], ACTA_BOARD_ID, ACTA_ESCALAMIENTO_COLUMN_ID, label)

                try:
                    create_update(item["id"], message)
                except Exception as e:
                    print(f"ESCALACION: item={item['id']} no se pudo publicar el update: {e}")

                print(f"ESCALACION: item={item['id']} escalado a '{label}' ({days} dias)")
                escalated += 1
                break

    print(f"ESCALACION: revision completa - {len(items)} items revisados, {escalated} escalados")
    return escalated


if __name__ == "__main__":
    print(check_escalaciones())
